"""
cipher status — Muestra el estado del contexto del repo actual.
"""

import os
import sys
import json
from datetime import datetime

GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'


def cmd_status(args: list):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from context_loader import ContextLoader

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║          cipher status                    ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    client, project = loader.resolve_project()

    # Estado del repo actual
    print(f"  {YELLOW}Repo actual{NC}")
    print(f"  {'─' * 40}")
    print(f"  Nombre   : {CYAN}{loader.repo_name}{NC}")
    print(f"  Ruta     : {loader.repo_path}")

    if client:
        print(f"  Cliente  : {GREEN}{client}{NC}")
        print(f"  Proyecto : {GREEN}{project}{NC}")
    else:
        print(f"  Cliente  : {RED}No registrado — ejecutá cipher init{NC}")

    # Estado del contexto
    brain_local = os.path.join(loader.repo_path, ".cipher")
    context_path = os.path.join(brain_local, "ACTIVE_CONTEXT.md")
    task_path = os.path.join(brain_local, "task-agent.md")
    alert_path = os.path.join(brain_local, "ALERT.md")

    print(f"\n  {YELLOW}Archivos .cipher/{NC}")
    print(f"  {'─' * 40}")
    _status_file(context_path, "ACTIVE_CONTEXT.md")
    _status_file(task_path, "task-agent.md")

    if os.path.exists(alert_path):
        print(f"  {RED}⚠ ALERT.md — Hay un alerta de impacto pendiente{NC}")
        print(f"    Leé: {alert_path}")
    else:
        _status_file(alert_path, "ALERT.md", optional=True)

    # Archivos de contexto en cipher
    if client and project:
        print(f"\n  {YELLOW}Contexto en cipher{NC}")
        print(f"  {'─' * 40}")
        client_dir = os.path.join(loader.cipher_dir, "clients", client, project)
        required = ["BUSINESS_RULES.md", "ARCHITECTURE.md", "DEPENDENCIES.md",
                   "RISK_MATRIX.md"]
        for fname in required:
            fpath = os.path.join(client_dir, fname)
            if os.path.exists(fpath):
                mtime = os.path.getmtime(fpath)
                age = _file_age(mtime)
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

    print()


def _status_file(path: str, label: str, optional: bool = False):
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        age = _file_age(mtime)
        print(f"  {GREEN}✓{NC} {label:<30} {CYAN}{age}{NC}")
    elif not optional:
        print(f"  {RED}✗{NC} {label:<30} {RED}no encontrado{NC}")


def _file_age(mtime: float) -> str:
    """Retorna la antigüedad de un archivo en formato legible."""
    now = datetime.now().timestamp()
    diff = int(now - mtime)

    if diff < 60:
        return "hace unos segundos"
    elif diff < 3600:
        return f"hace {diff // 60}m"
    elif diff < 86400:
        return f"hace {diff // 3600}h"
    else:
        return f"hace {diff // 86400}d"
