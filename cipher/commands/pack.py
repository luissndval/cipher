"""
cipher pack — Genera el context pack para una tarea.
Uso: cipher pack <descripción de tarea> [--repo <nombre>] [--provider <claude|gemini>]
"""

import os

from cipher.core.loader import ContextLoader
from cipher.index.indexer import RepoIndexer
from cipher.graph.builder import GraphBuilder
from cipher.pack.builder import PackBuilder

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
NC     = '\033[0m'


def cmd_pack(args: list):
    task_description = ""
    repo_name = None
    provider = "claude"
    task_id = None

    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo_name = args[i + 1]; i += 2
        elif args[i].startswith("--repo="):
            repo_name = args[i].split("=", 1)[1]; i += 1
        elif args[i] == "--provider" and i + 1 < len(args):
            provider = args[i + 1]; i += 2
        elif args[i].startswith("--provider="):
            provider = args[i].split("=", 1)[1]; i += 1
        elif args[i] == "--id" and i + 1 < len(args):
            task_id = args[i + 1]; i += 2
        elif not args[i].startswith("--"):
            task_description += (" " if task_description else "") + args[i]
            i += 1
        else:
            i += 1

    if not task_description:
        print(f"{RED}Uso: cipher pack <descripción de tarea> [--repo <nombre>] [--provider claude|gemini]{NC}")
        return

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║          cipher pack                      ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")
    print(f"  Task    : {task_description}")
    print(f"  Provider: {provider}\n")

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    # Detectar repo y cliente
    repo_path, resolved_repo_name, client_name = _resolve_repo(loader, repo_name)
    if not repo_path:
        print(f"{RED}✗ No se pudo detectar el repo. Usá --repo <nombre>.{NC}")
        return

    if not resolved_repo_name:
        resolved_repo_name = os.path.basename(repo_path)

    print(f"  Repo    : {CYAN}{resolved_repo_name}{NC}")
    print(f"  Path    : {repo_path}\n")

    # Cargar índice
    index_dir = os.path.join(loader.cipher_dir, ".cipher", "index", resolved_repo_name)
    index_path = os.path.join(index_dir, "index.json")
    graph_path = os.path.join(index_dir, "graph.json")

    if not os.path.exists(index_path):
        print(f"{YELLOW}⚠ Índice no encontrado. Indexando ahora...{NC}")
        try:
            indexer = RepoIndexer(repo_path, resolved_repo_name)
            repo_index = indexer.index()
            indexer.save(repo_index, index_dir)
        except Exception as e:
            print(f"{RED}✗ Error al indexar: {e}{NC}")
            return
    else:
        repo_index = RepoIndexer.load(index_path)

    if not os.path.exists(graph_path):
        print(f"{YELLOW}⚠ Grafo no encontrado. Construyendo...{NC}")
        try:
            graph = GraphBuilder(repo_index).build()
            GraphBuilder.save(graph, index_dir)
        except Exception as e:
            print(f"{RED}✗ Error al construir grafo: {e}{NC}")
            return
    else:
        graph = GraphBuilder.load(graph_path)

    print(f"  {GREEN}✓{NC} Índice cargado: {repo_index.stats.indexed_files} archivos")
    print(f"  {GREEN}✓{NC} Grafo cargado: {graph.node_count} nodos, {graph.edge_count} aristas\n")

    # Construir pack
    print(f"  {YELLOW}▸ Construyendo context pack...{NC}")
    builder = PackBuilder(
        repo_index=repo_index,
        graph=graph,
        repo_path=repo_path,
        cipher_dir=loader.cipher_dir,
        client_name=client_name,
    )
    pack = builder.build(task_description, provider=provider, task_id=task_id)

    # Guardar
    packs_dir = os.path.join(loader.cipher_dir, ".cipher", "packs", resolved_repo_name)
    md_path, manifest_path = PackBuilder.save(pack, packs_dir)

    m = pack.manifest
    print(f"\n{'─' * 50}")
    print(f"\n  {BLUE}RESULTADO{NC}\n")

    targets = [e for e in pack.entries if e.role == "target"]
    deps    = [e for e in pack.entries if e.role == "dependency"]
    pct     = 100 * m.tokens_used // m.token_budget if m.token_budget else 0

    print(f"  {GREEN}✓{NC} {len(targets)} archivo(s) objetivo")
    print(f"  {GREEN}✓{NC} {len(deps)} dependencia(s) incluida(s)")
    print(f"  {GREEN}✓{NC} Tokens: {m.tokens_used:,} / {m.token_budget:,} ({pct}% del budget {provider})")
    if pack.rules_content:
        print(f"  {GREEN}✓{NC} Rules incluidas")
    if pack.arch_snippet:
        print(f"  {GREEN}✓{NC} Architecture incluida")
    print(f"\n  Pack  : {md_path}")
    print(f"  Hash  : {m.context_pack_hash[:16]}...")
    print()

    if targets:
        print(f"  Archivos objetivo:")
        for e in targets:
            print(f"    {CYAN}{e.path}{NC}  (score={e.score:.1f}, ~{e.tokens:,}t)")
    print()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_repo(loader: ContextLoader, repo_name_hint: str | None):
    """
    Retorna (repo_path, repo_name, client_name) o (None, None, None).
    Prioridad: CWD → hint por nombre → primer repo registrado del cliente activo.
    """
    cwd = os.getcwd().replace("\\", "/")
    config = loader.config

    for client_name, client_data in config.get("clients", {}).items():
        if not isinstance(client_data, dict):
            continue
        for rname, rinfo in client_data.get("repos", {}).items():
            if not isinstance(rinfo, dict):
                continue
            rpath = rinfo.get("path", "").replace("\\", "/")
            if not rpath:
                continue

            # Coincidencia por CWD
            if cwd.startswith(rpath):
                return rpath, rname, client_name

            # Coincidencia por nombre explícito
            if repo_name_hint and rname == repo_name_hint:
                return rpath, rname, client_name

    # Fallback: usar CWD como repo si no hay config
    if not config.get("clients"):
        return os.getcwd(), os.path.basename(os.getcwd()), None

    return None, None, None
