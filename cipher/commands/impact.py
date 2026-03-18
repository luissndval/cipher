"""
cipher impact — Muestra el impact set de un archivo en el grafo de dependencias.
"""

import os

from cipher.graph.builder import GraphBuilder
from cipher.graph.schema import DependencyGraph
from cipher.core.loader import ContextLoader

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
NC     = '\033[0m'


def cmd_impact(args: list):
    if not args or args[0].startswith("--"):
        print(f"{RED}Uso: cipher impact <archivo> [--repo <nombre>] [--depth <n>]{NC}")
        return

    target_file = args[0].replace("\\", "/")
    repo_name = None
    max_depth = 10

    i = 1
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo_name = args[i + 1]; i += 2
        elif args[i].startswith("--repo="):
            repo_name = args[i].split("=", 1)[1]; i += 1
        elif args[i] == "--depth" and i + 1 < len(args):
            try:
                max_depth = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i].startswith("--depth="):
            try:
                max_depth = int(args[i].split("=", 1)[1])
            except ValueError:
                pass
            i += 1
        else:
            i += 1

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    # Resolver repo_name
    if not repo_name:
        repo_name = _detect_repo_name(loader)
    if not repo_name:
        print(f"{RED}✗ No se pudo detectar el repo. Usá --repo <nombre>.{NC}")
        return

    graph_path = os.path.join(loader.cipher_dir, ".cipher", "index", repo_name, "graph.json")
    if not os.path.exists(graph_path):
        print(f"{RED}✗ No se encontró grafo para '{repo_name}'. Ejecutá: cipher index{NC}")
        return

    graph: DependencyGraph = GraphBuilder.load(graph_path)

    # Normalizar target_file como rel_path
    rel_target = _normalize_target(target_file, graph)
    if rel_target is None:
        print(f"{RED}✗ '{target_file}' no está en el índice del repo '{repo_name}'.{NC}")
        _suggest_similar(target_file, graph)
        return

    impact = graph.impact_set(rel_target, max_depth=max_depth)

    print(f"\n{BLUE}Impact set — {CYAN}{rel_target}{NC}")
    print(f"  Repo    : {repo_name}")
    print(f"  Nodos   : {graph.node_count}   Aristas: {graph.edge_count}")
    print(f"  Max depth: {max_depth}\n")

    if not impact:
        print(f"  {YELLOW}Ningún archivo depende de este archivo.{NC}\n")
        return

    print(f"  {len(impact)} archivo(s) afectados:\n")
    current_depth = None
    for entry in impact:
        if entry.depth != current_depth:
            current_depth = entry.depth
            print(f"  {YELLOW}depth {current_depth}{NC}")
        via_str = f"  via {' → '.join(entry.via)}" if entry.via else ""
        print(f"    {GREEN}{entry.file_path}{NC}{via_str}")
    print()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _detect_repo_name(loader: ContextLoader) -> str | None:
    """Intenta detectar el repo activo desde el CWD."""
    cwd = os.getcwd().replace("\\", "/")
    config = loader.config
    for client_data in config.get("clients", {}).values():
        if not isinstance(client_data, dict):
            continue
        for repo_name, repo_info in client_data.get("repos", {}).items():
            if not isinstance(repo_info, dict):
                continue
            repo_path = repo_info.get("path", "").replace("\\", "/")
            if repo_path and cwd.startswith(repo_path):
                return repo_name
    return None


def _normalize_target(target: str, graph: DependencyGraph) -> str | None:
    """
    Intenta encontrar target como rel_path en el grafo.
    Acepta: rel_path exacto, nombre de archivo, o sufijo del path.
    """
    if target in graph.nodes:
        return target
    # Sufijo
    for path in graph.nodes:
        if path.endswith(target) or path.endswith("/" + target):
            return path
    return None


def _suggest_similar(target: str, graph: DependencyGraph):
    basename = os.path.basename(target)
    matches = [p for p in graph.nodes if os.path.basename(p) == basename]
    if matches:
        print(f"  {YELLOW}¿Quisiste decir?{NC}")
        for m in matches[:5]:
            print(f"    {m}")
