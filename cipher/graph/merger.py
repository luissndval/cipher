"""
cipher graph — GraphMerger
Merge en memoria de múltiples DependencyGraph en uno unificado.
Los paths se prefi jan con repo_key:: para evitar colisiones entre repos.
El grafo resultante NUNCA se persiste a disco.
"""

from datetime import datetime, timezone

from cipher.graph.schema import DependencyGraph, GraphNode, GraphEdge

BRAIN_VERSION = "0.2.0"


class GraphMerger:
    @staticmethod
    def prefix(repo_key: str, path: str) -> str:
        """Construye el path prefijado: 'repo_key::path'."""
        return f"{repo_key}::{path}"

    def merge(self, graphs: dict) -> DependencyGraph:
        """
        Recibe dict {repo_key: DependencyGraph}.
        Merge en memoria: todos los nodos y aristas de todos los grafos.
        Prefija los paths con repo_key:: para evitar colisiones.
        Retorna un único DependencyGraph unificado (no se persiste a disco).
        """
        merged_nodes: dict = {}
        merged_edges: list = []
        merged_external: dict = {}

        for repo_key, graph in graphs.items():
            # Prefijo de nodos
            for path, node in graph.nodes.items():
                new_path = self.prefix(repo_key, path)
                merged_nodes[new_path] = GraphNode(
                    path=new_path,
                    language=node.language,
                    symbol_count=node.symbol_count,
                )

            # Prefijo de aristas
            for edge in graph.edges:
                merged_edges.append(GraphEdge(
                    from_file=self.prefix(repo_key, edge.from_file),
                    to_file=self.prefix(repo_key, edge.to_file),
                    kind=edge.kind,
                    names=list(edge.names),
                ))

            # Merge de imports externos (acumular conteos)
            for module, count in graph.external_imports.items():
                merged_external[module] = merged_external.get(module, 0) + count

        repo_names = list(graphs.keys())
        merged_name = "+".join(repo_names) if repo_names else "merged"

        return DependencyGraph(
            repo_name=merged_name,
            repo_path="[merged-in-memory]",
            built_at=datetime.now(timezone.utc).isoformat(),
            brain_version=BRAIN_VERSION,
            nodes=merged_nodes,
            edges=merged_edges,
            external_imports=merged_external,
        )
