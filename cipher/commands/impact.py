"""
cipher impact — Muestra el impact set de un archivo en el grafo de dependencias.

Sin argumentos → lanza modo interactivo (InteractiveSession).
"""

import os

from cipher.graph.builder import GraphBuilder
from cipher.graph.schema import DependencyGraph
from cipher.core.loader import ContextLoader
from cipher.index.indexer import RepoIndexer

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
NC     = '\033[0m'


def cmd_impact(args: list):
    # Sin argumentos (o solo flags) → modo interactivo
    if not args or (len(args) == 1 and args[0].startswith("--")) or all(a.startswith("--") for a in args):
        _interactive_mode(args)
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

    # Si target_file parece un nombre de repo (sin extensión ni separadores)
    # y no pudimos detectar repo desde CWD, intentarlo como repo → modo interactivo
    if not repo_name and _looks_like_repo_name(target_file):
        candidate = _resolve_repo_name(target_file, loader)
        if candidate:
            _interactive_mode(["--repo", candidate, "--depth", str(max_depth)])
            return

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
        rel_target = _fuzzy_pick(target_file, graph, repo_name)
    if rel_target is None:
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


# ─── Modo interactivo ─────────────────────────────────────────────────────────

def _interactive_mode(args: list):
    """Lanza InteractiveSession cuando no se especifica archivo directo."""
    repo_name = None
    max_depth = 10

    i = 0
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

    if not repo_name:
        repo_name = _detect_repo_name(loader)
    if not repo_name:
        repo_name = _pick_repo(loader)
    if not repo_name:
        return

    index_path = os.path.join(loader.cipher_dir, ".cipher", "index", repo_name, "index.json")
    graph_path = os.path.join(loader.cipher_dir, ".cipher", "index", repo_name, "graph.json")

    if not os.path.exists(graph_path):
        print(f"{RED}✗ No se encontró grafo para '{repo_name}'. Ejecutá: cipher index{NC}")
        return
    if not os.path.exists(index_path):
        print(f"{RED}✗ No se encontró índice para '{repo_name}'. Ejecutá: cipher index{NC}")
        return

    repo_index = RepoIndexer.load(index_path)
    graph = GraphBuilder.load(graph_path)

    if graph.node_count == 0:
        print(f"{RED}✗ El índice de '{repo_name}' está vacío (0 archivos).{NC}")
        print(f"  Ejecutá {YELLOW}cipher index{NC} dentro del repo para indexarlo.")
        return

    from cipher.interactive.prompt import InteractiveSession
    InteractiveSession(repo_index, graph, repo_name, max_depth).run()


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


def _fuzzy_pick(query: str, graph: DependencyGraph, repo_name: str) -> str | None:
    """
    Busca archivos que contengan `query` como substring (case-insensitive).
    Si hay un único match, lo usa directamente.
    Si hay varios, muestra lista numerada para que el usuario elija.
    """
    q = query.lower().replace("\\", "/")
    matches = [p for p in sorted(graph.nodes) if q in p.lower()]

    if not matches:
        print(f"{RED}✗ No se encontró ningún archivo que contenga '{query}' en '{repo_name}'.{NC}")
        return None

    if len(matches) == 1:
        print(f"  {YELLOW}→ Usando:{NC} {CYAN}{matches[0]}{NC}\n")
        return matches[0]

    print(f"\n  {YELLOW}'{query}' matchea {len(matches)} archivo(s) en '{repo_name}':{NC}\n")
    # Paginar si hay muchos
    page_size = 20
    shown = matches[:page_size]
    for i, path in enumerate(shown, 1):
        print(f"  {YELLOW}{i:>3}{NC}. {CYAN}{path}{NC}")
    if len(matches) > page_size:
        print(f"\n  {YELLOW}... y {len(matches) - page_size} más. Afinás la búsqueda con más texto.{NC}")

    print()
    try:
        raw = input(f"  Elegí un número (Enter para cancelar): ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return None

    if not raw:
        return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(shown):
            return shown[idx]
        print(f"{RED}✗ Número fuera de rango.{NC}")
        return None
    except ValueError:
        print(f"{RED}✗ Ingresá un número.{NC}")
        return None


def _pick_repo(loader: ContextLoader) -> str | None:
    """Lista todos los repos indexados y deja elegir uno interactivamente."""
    cipher_index_dir = os.path.join(loader.cipher_dir, ".cipher", "index")
    repos = []

    # Repos con grafo ya construido
    if os.path.isdir(cipher_index_dir):
        for name in sorted(os.listdir(cipher_index_dir)):
            graph_path = os.path.join(cipher_index_dir, name, "graph.json")
            if os.path.exists(graph_path):
                repos.append(name)

    if not repos:
        print(f"{RED}✗ No hay repos indexados. Ejecutá: cipher index{NC}")
        return None

    if len(repos) == 1:
        print(f"  {YELLOW}→ Repo:{NC} {CYAN}{repos[0]}{NC}")
        return repos[0]

    print(f"\n  {BLUE}Repos disponibles:{NC}\n")
    for i, name in enumerate(repos, 1):
        print(f"  {YELLOW}{i:>3}{NC}. {CYAN}{name}{NC}")
    print()

    try:
        raw = input(f"  Elegí un repo (número o nombre, Enter para cancelar): ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return None

    if not raw:
        return None

    # Por número
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(repos):
            return repos[idx]
    except ValueError:
        pass

    # Por nombre (case-insensitive)
    for name in repos:
        if name.lower() == raw.lower():
            return name

    print(f"{RED}✗ Repo no encontrado: '{raw}'{NC}")
    return None


def _looks_like_repo_name(s: str) -> bool:
    """True si el string no tiene extensión ni separadores de path — parece un nombre de repo."""
    return "/" not in s and "\\" not in s and "." not in s


def _resolve_repo_name(candidate: str, loader: ContextLoader) -> str | None:
    """
    Busca en la config un repo cuyo nombre coincida (case-insensitive) con candidate.
    Retorna el nombre exacto si lo encuentra.
    """
    c = candidate.lower()
    config = loader.config
    for client_data in config.get("clients", {}).values():
        if not isinstance(client_data, dict):
            continue
        for repo_name in client_data.get("repos", {}):
            if repo_name.lower() == c:
                return repo_name
    return None
