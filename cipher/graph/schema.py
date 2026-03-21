"""
cipher graph — Schema
Estructuras de datos del grafo de dependencias.

Terminología:
  - dependency  : A depende de B  (A importa B)  → edge A→B
  - dependent   : B es usado por A               → A es dependent de B
  - impact set  : dado un cambio en X, qué archivos se ven afectados transitivamente
"""

from dataclasses import dataclass
from typing import Optional
from collections import deque


@dataclass
class GraphNode:
    """Nodo del grafo — representa un archivo fuente."""
    path: str          # rel_path en el repo
    language: str
    symbol_count: int

    def to_dict(self) -> dict:
        return {"path": self.path, "language": self.language, "symbol_count": self.symbol_count}

    @classmethod
    def from_dict(cls, d: dict) -> "GraphNode":
        return cls(path=d["path"], language=d["language"], symbol_count=d.get("symbol_count", 0))


@dataclass
class GraphEdge:
    """Arista dirigida: from_file importa símbolos de to_file."""
    from_file: str     # archivo que importa
    to_file: str       # archivo importado (in-repo, resuelto)
    kind: str          # "import" (Fase 2); en fases futuras: "call", "inherit"
    names: list        # nombres importados (puede ser vacío)

    def to_dict(self) -> dict:
        return {
            "from_file": self.from_file,
            "to_file": self.to_file,
            "kind": self.kind,
            "names": self.names,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GraphEdge":
        return cls(
            from_file=d["from_file"],
            to_file=d["to_file"],
            kind=d.get("kind", "import"),
            names=d.get("names", []),
        )


@dataclass
class ImpactEntry:
    """Un archivo afectado por un cambio, con profundidad y ruta de dependencia."""
    file_path: str
    depth: int         # 1 = importa directamente el archivo cambiado
    via: list          # cadena de archivos intermedios (excluye origen y este archivo)

    def to_dict(self) -> dict:
        return {"file_path": self.file_path, "depth": self.depth, "via": self.via}

    @classmethod
    def from_dict(cls, d: dict) -> "ImpactEntry":
        return cls(file_path=d["file_path"], depth=d["depth"], via=d.get("via", []))


@dataclass
class DependencyGraph:
    """Grafo de dependencias completo de un repositorio."""
    repo_name: str
    repo_path: str
    built_at: str        # ISO 8601
    brain_version: str
    nodes: dict          # rel_path → GraphNode
    edges: list          # list[GraphEdge]
    external_imports: dict  # module → count (dependencias fuera del repo)

    # ─── Serialización ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "repo_name": self.repo_name,
            "repo_path": self.repo_path,
            "built_at": self.built_at,
            "brain_version": self.brain_version,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "external_imports": self.external_imports,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DependencyGraph":
        return cls(
            repo_name=d["repo_name"],
            repo_path=d["repo_path"],
            built_at=d.get("built_at", ""),
            brain_version=d.get("brain_version", ""),
            nodes={k: GraphNode.from_dict(v) for k, v in d.get("nodes", {}).items()},
            edges=[GraphEdge.from_dict(e) for e in d.get("edges", [])],
            external_imports=d.get("external_imports", {}),
        )

    # ─── Consultas básicas ────────────────────────────────────────────────────

    def dependencies_of(self, file_path: str) -> list:
        """Archivos que file_path importa directamente (outbound)."""
        return list({e.to_file for e in self.edges if e.from_file == file_path})

    def dependents_of(self, file_path: str) -> list:
        """Archivos que importan directamente a file_path (inbound)."""
        return list({e.from_file for e in self.edges if e.to_file == file_path})

    def edge_names(self, from_file: str, to_file: str) -> list:
        """Nombres importados entre dos archivos."""
        return [
            name
            for e in self.edges
            if e.from_file == from_file and e.to_file == to_file
            for name in e.names
        ]

    # ─── Impact set ───────────────────────────────────────────────────────────

    def impact_set(self, file_path: str, max_depth: int = 10) -> list:
        """
        BFS sobre el grafo invertido: dado file_path (archivo cambiado),
        retorna todos los archivos que transitivamente dependen de él.
        Retorna list[ImpactEntry] ordenado por (depth, file_path).
        """
        if file_path not in self.nodes:
            return []

        result: list[ImpactEntry] = []
        visited = {file_path}
        # queue: (current_node, depth, via_chain)
        queue = deque([(file_path, 0, [])])

        while queue:
            current, depth, via = queue.popleft()
            if depth >= max_depth:
                continue

            for dependent in self.dependents_of(current):
                if dependent not in visited:
                    visited.add(dependent)
                    # via es la cadena desde el origen hasta el predecesor inmediato
                    new_via = via + [current] if depth > 0 else [current]
                    result.append(ImpactEntry(
                        file_path=dependent,
                        depth=depth + 1,
                        via=new_via,
                    ))
                    queue.append((dependent, depth + 1, new_via))

        return sorted(result, key=lambda x: (x.depth, x.file_path))

    # ─── Propiedades ──────────────────────────────────────────────────────────

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def isolated_files(self) -> list:
        """Archivos sin ninguna arista (ni importan ni son importados)."""
        connected = set()
        for e in self.edges:
            connected.add(e.from_file)
            connected.add(e.to_file)
        return [p for p in self.nodes if p not in connected]

    @property
    def most_imported(self) -> list:
        """Top archivos por cantidad de dependents (más usados), ordenados desc."""
        counts: dict[str, int] = {}
        for e in self.edges:
            counts[e.to_file] = counts.get(e.to_file, 0) + 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)
