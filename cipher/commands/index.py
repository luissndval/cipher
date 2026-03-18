"""
cipher index — Genera el índice estructural de un repositorio.
Uso: cipher index [--repo <path>]
"""

import os

from cipher.core.loader import ContextLoader
from cipher.index.indexer import RepoIndexer

GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
BLUE   = "\033[0;34m"
CYAN   = "\033[0;36m"
NC     = "\033[0m"


def cmd_index(args: list):
    repo_path = os.getcwd()
    for i, arg in enumerate(args):
        if arg == "--repo" and i + 1 < len(args):
            repo_path = args[i + 1]
        elif arg.startswith("--repo="):
            repo_path = arg.split("=", 1)[1]
    repo_path = os.path.abspath(repo_path)

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║          cipher index                     ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    repo_name = os.path.basename(repo_path)
    output_dir = os.path.join(loader.cipher_dir, ".cipher", "index", repo_name)

    print(f"  Repo    : {CYAN}{repo_name}{NC}")
    print(f"  Path    : {repo_path}")
    print(f"  Output  : {output_dir}\n")

    indexer = RepoIndexer(repo_path, repo_name)
    repo_index = indexer.index(verbose=True)
    index_path = indexer.save(repo_index, output_dir)

    s = repo_index.stats
    lang_str = "  ".join(
        f"{lang}({count})"
        for lang, count in sorted(s.languages.items())
    )

    print(f"\n{'─' * 50}")
    print(f"\n  {BLUE}RESULTADO{NC}\n")

    ok_label = f"{GREEN}✓{NC}"
    warn_label = f"{YELLOW}⚠{NC}"

    print(f"  {ok_label} {s.indexed_files} archivos indexados", end="")
    if s.failed_files:
        print(f"  {YELLOW}({s.failed_files} con errores de parse){NC}")
    else:
        print()

    print(f"  {ok_label} {s.total_symbols} símbolos extraídos")
    print(f"  {ok_label} {s.total_imports} imports registrados")
    if lang_str:
        print(f"  {ok_label} Lenguajes: {lang_str}")
    print(f"  {ok_label} Duración  : {s.duration_seconds}s")
    print(f"\n  Índice guardado: {index_path}\n")
