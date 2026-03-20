"""
cipher session — Abre sesión con el agente elegido, con contexto y manifest.
"""

import os
import re
import sys
from datetime import datetime

from cipher.core.loader import ContextLoader
from cipher.memory.session import SessionStore
from cipher.agents.launcher import launch_agent
from cipher.core.paths import resolve_repo_path

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
NC     = '\033[0m'

WORK_ITEM_TYPES = {
    "1": "FEATURE",
    "2": "TASK",
    "3": "ERROR",
    "4": "HOTFIX",
}


def cmd_session(agent: str, args: list):
    """Punto de entrada para cipher claude."""

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║  cipheria {agent:<10} — Iniciando sesión  ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    # Resolver cliente/proyecto: auto-detección o selección manual
    client, project = loader.resolve_project()
    if not client:
        client, project = _select_client_project(loader)
        if not client:
            return

    print(f"  Cliente : {CYAN}{client}{NC}")

    # Seleccionar repo de trabajo
    repos = loader.config.get("clients", {}).get(client, {}).get("repos", {})
    repo_path, repo_name = _select_repo(repos, loader.repo_path, loader.repo_name)

    print(f"  Repo    : {CYAN}{repo_name}{NC}")
    print(f"  Path    : {CYAN}{repo_path}{NC}")

    # Inicializar sesión
    store = SessionStore(loader.cipher_dir)
    session = store.new_session(client, project, agent, repo_path)
    print(f"  Sesión  : {CYAN}{session['session_id'][:8]}...{NC}")

    # Verificar/generar contexto
    session_dir = loader.session_dir(client, project)
    context_path = os.path.join(session_dir, "ACTIVE_CONTEXT.md")

    if not loader.context_exists():
        print(f"\n  {YELLOW}No encontré contexto generado. Generando...{NC}")
        context = loader.assemble_context(client, project, mode="summary")
        context_path = loader.save_context(context, client, project)
        print(f"  {GREEN}✓ Contexto generado: {context_path}{NC}")
    else:
        print(f"  {GREEN}✓ Contexto cargado: {context_path}{NC}")

    store.attach_context(session, context_path)

    # Crear task-agent.md
    os.makedirs(session_dir, exist_ok=True)
    task_path = _create_task(session_dir, client, project, repo_name, repo_path)
    store.attach_task(session, task_path)

    # Guardar manifest antes de lanzar el agente
    manifest_path = store.save_manifest(session, client, project)
    print(f"  {GREEN}✓ Manifest: {manifest_path}{NC}")

    # Lanzar agente
    print(f"\n  {YELLOW}Lanzando {agent}...{NC}\n")
    launch_agent(agent, context_path, task_path, repo_path)

    # Cerrar sesión y actualizar manifest
    store.close_session(session)
    store.save_manifest(session, client, project)


# ─── Selección ────────────────────────────────────────────────────────────────

def _select_client_project(loader: ContextLoader) -> tuple:
    """Cuando no se detecta el repo por CWD, permite elegir manualmente."""
    clients = loader.config.get("clients", {})

    if not clients:
        print(f"{YELLOW}⚠ No hay clientes registrados en cipheria.{NC}")
        answer = input("  ¿Registrar un proyecto ahora con 'cipheria init'? [S/n]: ").strip().lower()
        if answer in ["", "s", "si", "y"]:
            from cipher.commands.init import cmd_init
            cmd_init(args=[])
            loader.config = loader._load_config()
            return loader.resolve_project()
        return None, None

    options = []
    for client_name, client_data in clients.items():
        repos = client_data.get("repos", {}) if isinstance(client_data, dict) else {}
        for repo_key, repo_data in repos.items():
            rpath = resolve_repo_path(client_data, repo_key, repo_data) if isinstance(repo_data, dict) else None
            if isinstance(repo_data, dict) and rpath:
                repo_data = {**repo_data, "path": rpath}  # inyectar path resuelto
            options.append((client_name, repo_key, repo_data))

    if not options:
        print(f"{RED}✗ No hay repos registrados. Ejecutá 'cipheria init' primero.{NC}")
        return None, None

    print(f"\n  {YELLOW}▸ Repos registrados:{NC}")
    for i, (client_name, repo_key, repo_data) in enumerate(options, 1):
        path = repo_data.get("path", "—") if isinstance(repo_data, dict) else "—"
        print(f"  {i}. {CYAN}{client_name}/{repo_key}{NC}  ({path})")

    while True:
        choice = input(f"\n  Seleccioná el repo [1-{len(options)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            client_name, repo_key, repo_data = options[int(choice) - 1]
            loader.client = client_name
            loader.project = repo_key
            if isinstance(repo_data, dict):
                loader.repo_path = repo_data.get("path", loader.repo_path)
                loader.repo_name = repo_data.get("name", repo_key)
            return client_name, repo_key
        print(f"  {RED}Opción inválida.{NC}")


def _select_repo(repos: dict, default_path: str, default_name: str) -> tuple:
    if not repos:
        return default_path, default_name
    repo_list = list(repos.items())
    if len(repo_list) == 1:
        repo_key, repo_data = repo_list[0]
        return repo_data.get("path", default_path), repo_data.get("name", repo_key)

    print(f"\n  {YELLOW}▸ Repos disponibles:{NC}")
    for i, (repo_key, repo_data) in enumerate(repo_list, 1):
        path = repo_data.get("path", "—")
        print(f"  {i}. {CYAN}{repo_key}{NC}  ({path})")

    while True:
        choice = input(f"  Seleccioná el repo [1-{len(repo_list)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(repo_list):
            repo_key, repo_data = repo_list[int(choice) - 1]
            return repo_data.get("path", default_path), repo_data.get("name", repo_key)
        print(f"  {RED}Opción inválida.{NC}")


# ─── Task ─────────────────────────────────────────────────────────────────────

def _make_branch_name(work_type: str, number: str, title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\s]", "", title)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug).upper()
    return f"{work_type}-{number}-{slug}"


def _create_task(session_dir: str, client: str, project: str,
                 repo_name: str, repo_path: str) -> str:
    os.makedirs(session_dir, exist_ok=True)
    task_path = os.path.join(session_dir, "task-agent.md")

    print(f"\n  {YELLOW}▸ Tipo de work item:{NC}")
    for key, label in WORK_ITEM_TYPES.items():
        print(f"    {key}. {label}")
    while True:
        choice = input(f"  Seleccioná [1-{len(WORK_ITEM_TYPES)}]: ").strip()
        if choice in WORK_ITEM_TYPES:
            work_type = WORK_ITEM_TYPES[choice]
            break
        print(f"  {RED}Opción inválida.{NC}")

    number = input("  Número de ticket (ej: 142): ").strip()
    if not number:
        number = datetime.now().strftime("%Y%m%d%H%M")

    title = input("  Título breve (ej: agregar login con google): ").strip()
    if not title:
        title = "SIN-TITULO"

    description = input("  Descripción detallada (Enter para saltar): ").strip()
    if not description:
        description = "—"

    link = input("  Link del ticket (ej: https://linear.app/... — Enter para saltar): ").strip()

    branch_name = _make_branch_name(work_type, number, title)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    link_line = f"\n**Link:** {link}" if link else ""

    content = f"""# [{work_type}-{number}] {title}
> Generado por cipher | {now}

## Tipo
{work_type}

## Descripción
{description}{link_line}

## Contexto del proyecto
- **Repo:** {repo_name}
- **Path:** {repo_path}
- **Cliente:** {client}
- **Proyecto:** {project}
- **Branch:** `{branch_name}`

## Instrucciones para el agente
Ejecutá estos pasos **en orden** dentro del repo en `{repo_path}`:

### PASO 1 — Preparar branch
```bash
git checkout -b {branch_name}
```
Verificá que estás en la branch correcta antes de escribir cualquier código.

### PASO 2 — Implementar
- Seguí el TASK_FLOW y las convenciones del contexto del proyecto.
- Evaluá impacto cruzado antes de modificar interfaces públicas.
- Scope limitado: solo lo necesario para este ticket.

### PASO 3 — Commit y push
```bash
git add -p
git commit -m "{work_type}-{number}: <descripción corta del cambio>"
git push -u origin {branch_name}
```

### PASO 4 — Crear Pull Request
```bash
gh pr create \\
  --title "[{work_type}-{number}] {title}" \\
  --body "## Qué hace este PR\\n\\n{description}\\n\\n## Cómo probar\\n- [ ] ..." \\
  --base main
```

### PASO 5 — Cerrar sesión
Ejecutá `cipheria update` para actualizar el contexto con los cambios realizados.

## Estado
- [ ] Branch creada
- [ ] Implementado
- [ ] Tests pasando
- [ ] Commit y push
- [ ] PR creado
- [ ] Contexto actualizado
"""
    with open(task_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  {GREEN}✓ Task creada  : {task_path}{NC}")
    print(f"  {GREEN}✓ Branch target: {branch_name}{NC}")
    return task_path
