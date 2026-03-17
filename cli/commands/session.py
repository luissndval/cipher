"""
brain session — Abre una sesión con el agente elegido, con contexto cargado.
Maneja: claude, gemini, codex, aider
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

WORK_ITEM_TYPES = {
    "1": "FEATURE",
    "2": "TASK",
    "3": "ERROR",
    "4": "HOTFIX",
}

GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'


def cmd_session(agent: str, args: list):
    """Punto de entrada para cipher claude / cipher gemini / cipher codex."""

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from context_loader import ContextLoader
    from providers import get_analysis_provider

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║     cipher {agent:<10} — Iniciando sesión  ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")

    # 1. Cargar context loader
    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    # 2. Resolver cliente/proyecto
    client, project = loader.resolve_project()

    if not client:
        print(f"{YELLOW}⚠ No encontré este repo en cipher.{NC}")
        answer = input(f"  ¿Querés registrarlo ahora con 'cipher init'? [S/n]: ").strip().lower()
        if answer in ["", "s", "si", "y"]:
            from commands.init import cmd_init
            cmd_init(args=[])
            loader = ContextLoader()
            client, project = loader.resolve_project()
            if not client:
                print(f"{RED}✗ No se pudo resolver el proyecto.{NC}")
                return
        else:
            return

    print(f"  Cliente : {CYAN}{client}{NC}")

    # 3. Seleccionar repo de trabajo
    repos = loader.config.get("clients", {}).get(client, {}).get("repos", {})
    repo_path, repo_name = _select_repo(repos, loader.repo_path, loader.repo_name)

    print(f"  Repo    : {CYAN}{repo_name}{NC}")
    print(f"  Path    : {CYAN}{repo_path}{NC}")

    # 4. Verificar/generar contexto (guardado en cipher project, no en repo cliente)
    session_dir = loader.session_dir(client, project)
    context_path = os.path.join(session_dir, "ACTIVE_CONTEXT.md")

    if not loader.context_exists():
        print(f"\n  {YELLOW}No encontré contexto generado. Generando...{NC}")
        context = loader.assemble_context(client, project, mode="summary")
        context_path = loader.save_context(context, client, project)
        print(f"  {GREEN}✓ Contexto generado: {context_path}{NC}")
    else:
        print(f"  {GREEN}✓ Contexto cargado: {context_path}{NC}")

    # 5. Crear task-agent.md en el cipher project (no en el repo cliente)
    os.makedirs(session_dir, exist_ok=True)
    task_path = create_task(session_dir, client, project, repo_name, repo_path)

    # 6. Lanzar el agente
    print(f"\n  {YELLOW}Lanzando {agent}...{NC}\n")
    launch_agent(agent, context_path, task_path, repo_path)



def _select_repo(repos: dict, default_path: str, default_name: str) -> tuple:
    """Muestra los repos disponibles del cliente y permite seleccionar uno."""
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


def _make_branch_name(work_type: str, number: str, title: str) -> str:
    """Genera el nombre de branch: TIPO-NUMERO-TITULO-EN-MAYUSCULAS."""
    slug = re.sub(r"[^a-zA-Z0-9\s]", "", title)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug).upper()
    return f"{work_type}-{number}-{slug}"


def create_task(session_dir: str, client: str, project: str, repo_name: str, repo_path: str) -> str:
    """Crea task-agent.md en el directorio de sesión del cipher project."""
    os.makedirs(session_dir, exist_ok=True)
    task_path = os.path.join(session_dir, "task-agent.md")

    # Tipo de work item
    print(f"\n  {YELLOW}▸ Tipo de work item:{NC}")
    for key, label in WORK_ITEM_TYPES.items():
        print(f"    {key}. {label}")
    while True:
        choice = input(f"  Seleccioná [1-{len(WORK_ITEM_TYPES)}]: ").strip()
        if choice in WORK_ITEM_TYPES:
            work_type = WORK_ITEM_TYPES[choice]
            break
        print(f"  {RED}Opción inválida.{NC}")

    number = input(f"  Número de ticket (ej: 142): ").strip()
    if not number:
        number = datetime.now().strftime("%Y%m%d%H%M")

    title = input(f"  Título breve (ej: agregar login con google): ").strip()
    if not title:
        title = "SIN-TITULO"

    description = input(f"  Descripción detallada (Enter para saltar): ").strip()
    if not description:
        description = "—"

    branch_name = _make_branch_name(work_type, number, title)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    content = f"""# [{work_type}-{number}] {title}
> Generado por cipher | {now}

## Tipo
{work_type}

## Descripción
{description}

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
Cuando la implementación esté lista:
```bash
git add -p           # revisá cada cambio antes de stagear
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
Si `gh` no está disponible, indicá la URL del repo para crear el PR manualmente.

### PASO 5 — Cerrar sesión
Ejecutá `cipher update` para actualizar el contexto con los cambios realizados.

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


def launch_agent(agent: str, context_path: str, task_path: str, repo_path: str):
    """Lanza el agente de codificación con el contexto cargado."""
    with open(context_path, encoding="utf-8") as f:
        context_content = f.read()

    with open(task_path, encoding="utf-8") as f:
        task_content = f.read()

    _launch_claude(context_content, task_content, repo_path)


def _launch_claude(context: str, task: str, repo_path: str):
    """Lanza Claude Code inyectando contexto via CLAUDE.md temporal.
    El archivo se borra automáticamente al salir de la sesión.
    """
    if not _check_command("claude"):
        print(f"{RED}✗ Claude Code no está instalado.{NC}")
        print(f"  Instalalo con: npm install -g @anthropic-ai/claude-code")
        return

    claude_md_path = os.path.join(repo_path, "CLAUDE.md")
    claude_md_existed = os.path.exists(claude_md_path)
    original_content = None
    if claude_md_existed:
        with open(claude_md_path, encoding="utf-8", errors="ignore") as f:
            original_content = f.read()

    claude_md_content = f"""# Contexto cipher — SESIÓN ACTIVA (se borra al salir)

## TAREA ACTUAL
{task}

## CONTEXTO DEL PROYECTO
{context}
"""
    try:
        with open(claude_md_path, "w", encoding="utf-8") as f:
            f.write(claude_md_content)
        print(f"  {GREEN}✓ Contexto inyectado (CLAUDE.md temporal){NC}")
        print(f"  Iniciando Claude Code en {repo_path}...\n")
        initial_prompt = (
            "Leé el CLAUDE.md completo. "
            "Empezá por el PASO 1: creá la branch indicada en la sección TAREA ACTUAL. "
            "Luego implementá lo requerido siguiendo los pasos en orden. "
            "Al terminar, hacé commit, push y creá el PR según las instrucciones."
        )
        subprocess.run(["claude", initial_prompt], cwd=repo_path)
    finally:
        # Siempre limpiar al salir — con error o sin él
        if claude_md_existed and original_content is not None:
            with open(claude_md_path, "w", encoding="utf-8") as f:
                f.write(original_content)
        elif os.path.exists(claude_md_path):
            os.remove(claude_md_path)
        print(f"  {GREEN}✓ CLAUDE.md eliminado del repo cliente{NC}")


def _check_command(cmd: str) -> bool:
    """Verifica si un comando está disponible en el sistema."""
    try:
        result = subprocess.run(
            ["which", cmd] if os.name != "nt" else ["where", cmd],
            capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False
