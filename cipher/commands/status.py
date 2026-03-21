"""
cipher status — Muestra el estado del contexto del repo actual.
"""

import os
from datetime import datetime

from cipher.core.loader import ContextLoader
from cipher.memory.session import SessionStore

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
NC     = '\033[0m'


def cmd_status(args: list):
    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║        cipheria status                    ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    client, project = loader.resolve_project()

    print(f"  {YELLOW}Repo actual{NC}")
    print(f"  {'─' * 40}")
    print(f"  Nombre   : {CYAN}{loader.repo_name}{NC}")
    print(f"  Ruta     : {loader.repo_path}")

    if client:
        print(f"  Cliente  : {GREEN}{client}{NC}")
        print(f"  Proyecto : {GREEN}{project}{NC}")
    else:
        print(f"  Cliente  : {RED}No registrado — ejecutá cipheria init{NC}")

    # Contexto en cipher
    if client and project:
        print(f"\n  {YELLOW}Contexto en cipher{NC}")
        print(f"  {'─' * 40}")
        client_dir = os.path.join(loader.cipher_dir, "clients", client, project)
        for fname in ["BUSINESS_RULES.md", "ARCHITECTURE.md", "DEPENDENCIES.md", "RISK_MATRIX.md"]:
            fpath = os.path.join(client_dir, fname)
            if os.path.exists(fpath):
                age = _file_age(os.path.getmtime(fpath))
                print(f"  {GREEN}✓{NC} {fname:<30} {CYAN}{age}{NC}")
            else:
                print(f"  {YELLOW}○{NC} {fname:<30} {YELLOW}no generado{NC}")

    # Repos del cliente
    if client:
        print(f"\n  {YELLOW}Repos del cliente {client}{NC}")
        print(f"  {'─' * 40}")
        client_data = loader.config.get("clients", {}).get(client, {})
        repos = client_data.get("repos", {})
        for repo_name, repo_data in repos.items():
            repo_path = repo_data.get("path", "")
            alert = os.path.join(repo_path, ".cipher", "ALERT.md") if repo_path else ""
            has_alert = os.path.exists(alert) if alert else False
            indicator = f"{RED}⚠ ALERT{NC}" if has_alert else f"{GREEN}OK{NC}"
            marker = "→" if repo_name == project else " "
            print(f"  {marker} {repo_name:<30} {indicator}")

    # Última sesión
    if client and project:
        store = SessionStore(loader.cipher_dir)
        last = store.load_latest_manifest(client, project)
        if last:
            print(f"\n  {YELLOW}Última sesión{NC}")
            print(f"  {'─' * 40}")
            print(f"  ID      : {CYAN}{last.get('session_id', '—')[:8]}...{NC}")
            print(f"  Agente  : {last.get('agent', '—')}")
            print(f"  Estado  : {last.get('status', '—')}")
            print(f"  Fecha   : {last.get('timestamp', '—')[:19].replace('T', ' ')}")

    print()


def _file_age(mtime: float) -> str:
    diff = int(datetime.now().timestamp() - mtime)
    if diff < 60:
        return "hace unos segundos"
    if diff < 3600:
        return f"hace {diff // 60}m"
    if diff < 86400:
        return f"hace {diff // 3600}h"
    return f"hace {diff // 86400}d"
