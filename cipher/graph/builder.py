"""
cipher graph — GraphBuilder
Construye un DependencyGraph a partir de un RepoIndex.
Determinístico: usa ImportResolver para mapear imports a archivos del repo.
"""

import json
import os
from datetime import datetime, timezone

from cipher.index.schema import RepoIndex
from cipher.graph.schema import DependencyGraph, GraphNode, GraphEdge
from cipher.graph.resolver import ImportResolver

BRAIN_VERSION = "0.2.0"


class GraphBuilder:
    def __init__(self, repo_index: RepoIndex):
        self.repo_index = repo_index
        self._known_files = {f.path for f in repo_index.files}
        self._resolver = ImportResolver(self._known_files)

    def build(self) -> DependencyGraph:
        nodes: dict = {}
        edges: list = []
        external_imports: dict = {}

        # Crear nodos
        for file_index in self.repo_index.files:
            nodes[file_index.path] = GraphNode(
                path=file_index.path,
                language=file_index.language,
                symbol_count=len(file_index.symbols),
            )

        # Resolver imports → aristas
        for file_index in self.repo_index.files:
            rel_path = file_index.path
            for imp in file_index.imports:
                resolved_list = self._resolver.resolve(imp, rel_path, file_index.language)
                if resolved_list:
                    for resolved in resolved_list:
                        edges.append(GraphEdge(
                            from_file=rel_path,
                            to_file=resolved,
                            kind="import",
                            names=list(imp.names) if imp.names else [],
                        ))
                else:
                    # Import externo: contar por módulo
                    mod = imp.module
                    external_imports[mod] = external_imports.get(mod, 0) + 1

        return DependencyGraph(
            repo_name=self.repo_index.repo_name,
            repo_path=self.repo_index.repo_path,
            built_at=datetime.now(timezone.utc).isoformat(),
            brain_version=BRAIN_VERSION,
            nodes=nodes,
            edges=edges,
            external_imports=external_imports,
        )

    # ─── Persistencia ─────────────────────────────────────────────────────────

    @staticmethod
    def save(graph: DependencyGraph, output_dir: str) -> str:
        """Guarda graph.json en output_dir. Retorna la ruta del archivo."""
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "graph.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(graph.to_dict(), f, indent=2, ensure_ascii=False)
        return path

    @staticmethod
    def load(path: str) -> DependencyGraph:
        """Carga un graph.json desde disco."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return DependencyGraph.from_dict(data)
