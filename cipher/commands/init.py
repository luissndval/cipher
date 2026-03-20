"""
cipher init — Onboarding automático
Escanea repos .git, registra clientes y genera contexto con IA.
"""

import os
import json

from cipher.core.loader import ContextLoader
from cipher.analysis.providers import get_analysis_provider, save_provider_config
from cipher.analysis.scanner import (
    scan_git_repos, get_repo_structure, get_repo_info,
    generate_context_files, detect_dependencies,
)

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
NC     = '\033[0m'


def cmd_init(args: list):
    scan_path = os.getcwd()
    for i, arg in enumerate(args):
        if arg == "--scan" and i + 1 < len(args):
            scan_path = args[i + 1]
        elif arg.startswith("--scan="):
            scan_path = arg.split("=", 1)[1]
    scan_path = os.path.abspath(scan_path)

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║        cipheria init — Onboarding         ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")
    print(f"  Escaneando: {scan_path}\n")

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    repos = scan_git_repos(scan_path)
    if not repos:
        print(f"{RED}✗ No se encontraron repositorios .git en {scan_path}{NC}")
        return

    print(f"  Encontré {len(repos)} repositorio(s):\n")

    selected_repos = []
    for repo_path in repos:
        repo_name = os.path.basename(repo_path)
        answer = input(f"  ¿Registrar {CYAN}{repo_name}{NC}? [S/n]: ").strip().lower()
        if answer in ["", "s", "si", "sí", "y", "yes"]:
            selected_repos.append((repo_name, repo_path))
        else:
            print(f"  {YELLOW}→ Saltando {repo_name}{NC}")

    if not selected_repos:
        print(f"\n{YELLOW}No se seleccionó ningún repo. Saliendo.{NC}")
        return

    print()
    client_name = input(f"  ¿Nombre del cliente para estos repos? ").strip()
    if not client_name:
        client_name = os.path.basename(scan_path)
    client_name = client_name.lower().replace(" ", "-")

    print(f"\n  {YELLOW}¿Qué provider usar para analizar los repos?{NC}")
    print(f"    {YELLOW}1{NC}. Gemini  {CYAN}(recomendado — 400k contexto){NC}")
    print(f"    {YELLOW}2{NC}. Claude  (60k contexto)")
    choice = input(f"\n  Elegí [1/2, Enter = Gemini]: ").strip()
    preferred = "claude" if choice == "2" else "gemini"

    provider = get_analysis_provider(preferred)
    if not provider.can_analyze():
        provider = _configure_api_key(preferred)
        if not provider or not provider.can_analyze():
            print(f"\n{RED}✗ Se necesita una API key para analizar repos.{NC}")
            return

    print(f"\n{YELLOW}▸ Analizando repos con {provider.name}...{NC}\n")

    client_dir = os.path.join(loader.cipher_dir, "clients", client_name)
    os.makedirs(client_dir, exist_ok=True)

    repo_configs = {}
    for repo_name, repo_path in selected_repos:
        print(f"  Analizando {CYAN}{repo_name}{NC}...")
        repo_dir = os.path.join(client_dir, repo_name)
        os.makedirs(repo_dir, exist_ok=True)

        max_chars = getattr(provider, "max_context_chars", 60_000)
        repo_structure = get_repo_structure(repo_path)
        repo_info = get_repo_info(repo_path, max_total=max_chars)

        generate_context_files(provider, repo_name, repo_path, repo_structure, repo_info, repo_dir)

        repo_configs[repo_name] = {
            "name": repo_name,
            "path": repo_path,
            "owner": "",
            "depends_on": [],
            "consumed_by": [],
        }
        print(f"  {GREEN}✓ {repo_name} — contexto generado{NC}")

        # F1-5: Indexación estructural (no bloqueante — complementa el análisis LLM)
        try:
            from cipher.index.indexer import RepoIndexer
            index_out = os.path.join(loader.cipher_dir, ".cipher", "index", repo_name)
            ri = RepoIndexer(repo_path, repo_name).index()
            RepoIndexer(repo_path, repo_name).save(ri, index_out)
            print(f"  {GREEN}✓ {repo_name} — índice estructural: "
                  f"{ri.stats.total_symbols} símbolos, {ri.stats.total_imports} imports{NC}")
        except Exception as e:
            print(f"  {YELLOW}⚠ Indexación estructural falló (no bloqueante): {e}{NC}")

    if len(selected_repos) > 1:
        print(f"\n  {YELLOW}Detectando dependencias entre repos...{NC}")
        repo_configs = detect_dependencies(provider, client_name, repo_configs, selected_repos)

    _update_client_config(loader, client_name, repo_configs)

    for repo_name, repo_path in selected_repos:
        os.makedirs(os.path.join(repo_path, ".cipher"), exist_ok=True)
        _update_gitignore(repo_path)

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║         ✓ Onboarding completo            ║")
    print(f"╚══════════════════════════════════════════╝{NC}")
    print(f"\n  Cliente : {client_name}")
    print(f"  Repos   : {len(selected_repos)}")
    print(f"  Contexto: {client_dir}")
    print(f"\n  Próximo paso:")
    print(f"  {YELLOW}cipheria claude{NC}   → iniciar sesión de desarrollo\n")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _update_client_config(loader: ContextLoader, client_name: str, repo_configs: dict):
    config = loader.config
    if "clients" not in config:
        config["clients"] = {}
    config["clients"][client_name] = {"repos": repo_configs}
    config_path = os.path.join(loader.cipher_dir, ".cipher", "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _configure_api_key(preferred: str):
    info = {
        "gemini": ("google", "Google Gemini", "aistudio.google.com/app/apikey"),
        "claude": ("anthropic", "Anthropic Claude", "console.anthropic.com/settings/keys"),
    }
    provider_key, label, url = info.get(preferred, (preferred, preferred, ""))
    print(f"\n  {YELLOW}Se necesita una API key de {label}.{NC}")
    print(f"  Obtené la tuya en: {BLUE}https://{url}{NC}")
    api_key = input(f"  Pegá tu API key: ").strip()
    if not api_key:
        return None
    save_provider_config(provider_key, {"api_key": api_key, "auth": "apikey"})
    return get_analysis_provider(preferred)


def _update_gitignore(repo_path: str):
    gitignore_path = os.path.join(repo_path, ".gitignore")
    cipher_entries = [
        "# cipher — archivos generados automáticamente",
        "CLAUDE.md",
        ".cipher/ACTIVE_CONTEXT.md",
        ".cipher/task-agent.md",
        ".cipher/ALERT.md",
    ]
    existing = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path) as f:
            existing = f.read()
    additions = [e for e in cipher_entries if e not in existing]
    if additions:
        with open(gitignore_path, "a") as f:
            f.write("\n")
            for entry in additions:
                f.write(f"{entry}\n")
