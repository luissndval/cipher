"""
cipher update — Actualiza el contexto de cipher después de un cambio.
Detecta git diff, analiza con IA, propone cambios y genera ALERT.md si hay impacto cruzado.
"""

import os
import sys
import json
import re
from datetime import datetime

GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'


def cmd_update(args: list):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from context_loader import ContextLoader
    from providers import get_analysis_provider

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║       cipher update — Actualizar contexto  ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")

    # 1. Cargar loader y resolver proyecto
    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    client, project = loader.resolve_project()
    if not client:
        print(f"{RED}✗ Este repo no está registrado en cipher.{NC}")
        print(f"  Ejecutá 'cipher init' primero.")
        return

    print(f"  Repo    : {CYAN}{loader.repo_name}{NC}")
    print(f"  Cliente : {CYAN}{client}{NC}")

    # 2. Obtener git diff
    diff = loader.get_git_diff()
    if not diff:
        recent = loader.get_recent_commits(3)
        print(f"\n  {YELLOW}No hay cambios pendientes en git.{NC}")
        if recent:
            print(f"  Últimos commits:\n")
            for line in recent.split("\n"):
                print(f"    {line}")
        answer = input(f"\n  ¿Analizar el último commit de todas formas? [s/N]: ").strip().lower()
        if answer not in ["s", "si", "y"]:
            print(f"  {YELLOW}Sin cambios para analizar.{NC}")
            return
        # Usar diff del último commit
        import subprocess
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"],
            capture_output=True, text=True, cwd=loader.repo_path
        )
        diff = result.stdout.strip()

    # Mostrar resumen del diff
    diff_lines = diff.count('\n')
    files_changed = len([l for l in diff.split('\n') if l.startswith('diff --git')])
    print(f"\n  Cambios detectados: {files_changed} archivo(s), ~{diff_lines} líneas\n")

    # 3. Leer task-agent.md si existe
    task_path = os.path.join(loader.repo_path, ".cipher", "task-agent.md")
    task_content = ""
    if os.path.exists(task_path):
        with open(task_path) as f:
            task_content = f.read()
        print(f"  {GREEN}✓ task-agent.md encontrado{NC}")
    else:
        print(f"  {YELLOW}⚠ No encontré task-agent.md{NC}")
        task_content = input(f"  Describí brevemente qué cambió: ").strip()

    # 4. Elegir provider de análisis (Gemini por defecto)
    print(f"\n  {YELLOW}¿Qué provider usar para analizar el cambio?{NC}")
    print(f"    1. Gemini  {CYAN}(recomendado){NC}")
    print(f"    2. Claude")
    choice = input(f"  [1/2, Enter=Gemini]: ").strip()
    preferred = "claude" if choice == "2" else "gemini"

    provider = get_analysis_provider(preferred)
    if not provider.is_configured():
        print(f"{RED}✗ API key no configurada para {preferred}.{NC}")
        return

    # 5. Analizar con IA
    print(f"\n  {YELLOW}Analizando cambios con {provider.name}...{NC}")

    system_prompt = """Sos un arquitecto de software que analiza cambios en repositorios.
Tu tarea es determinar qué cambió arquitecturalmente y proponer actualizaciones al contexto del proyecto.
Respondés siempre en JSON válido, sin markdown, sin explicaciones fuera del JSON."""

    try:
        response = provider.analyze_diff(system_prompt, diff, task_content)
        analysis = parse_analysis(response)
    except Exception as e:
        print(f"{RED}✗ Error al analizar: {e}{NC}")
        return

    # 6. Mostrar análisis
    print(f"\n{'─' * 50}")
    print(f"\n  {BLUE}ANÁLISIS DEL CAMBIO{NC}\n")
    print(f"  Resumen: {analysis.get('summary', 'Sin resumen')}")
    print(f"  Riesgo : {_risk_color(analysis.get('impact_level', 'BAJO'))}")

    cross_impact = analysis.get("cross_repo_impact", [])
    if cross_impact:
        print(f"\n  {YELLOW}⚠ IMPACTO CRUZADO DETECTADO:{NC}")
        for item in cross_impact:
            repo = item.get("repo") or item if isinstance(item, str) else str(item)
            reason = item.get("reason", "") if isinstance(item, dict) else ""
            print(f"    → {repo}: {reason}")

    context_updates = analysis.get("context_updates", {})
    if context_updates:
        print(f"\n  Archivos de contexto a actualizar:")
        for fname in context_updates.keys():
            print(f"    → {fname}")

    print(f"\n{'─' * 50}\n")

    # 7. Confirmar actualización
    answer = input(f"  ¿Actualizo el contexto en cipher? [S/n]: ").strip().lower()
    if answer not in ["", "s", "si", "y"]:
        print(f"  {YELLOW}Actualización cancelada.{NC}")
        return

    # 8. Aplicar actualizaciones
    client_project_dir = os.path.join(loader.cipher_dir, "clients", client, project)
    os.makedirs(client_project_dir, exist_ok=True)

    updated_files = []
    for filename, new_content in context_updates.items():
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
        file_path = os.path.join(client_project_dir, filename)
        with open(file_path, "w") as f:
            f.write(new_content)
        updated_files.append(filename)
        print(f"  {GREEN}✓ Actualizado: {filename}{NC}")

    # 9. Generar ALERT.md en repos afectados
    if cross_impact:
        alert_content = analysis.get("alert_content") or _generate_alert(
            loader.repo_name, client, analysis
        )
        answer2 = input(f"\n  ¿Genero ALERT.md en los repos afectados? [S/n]: ").strip().lower()
        if answer2 in ["", "s", "si", "y"]:
            generate_alerts(loader, client, cross_impact, alert_content)

    # 10. Regenerar ACTIVE_CONTEXT.md
    context = loader.assemble_context(client, project, mode="summary")
    loader.save_context(context)
    print(f"  {GREEN}✓ ACTIVE_CONTEXT.md regenerado{NC}")

    # 11. Commit en cipher
    answer3 = input(f"\n  ¿Hacer commit en cipher? [S/n]: ").strip().lower()
    if answer3 in ["", "s", "si", "y"]:
        commit_cipher(loader.cipher_dir, loader.repo_name, analysis.get("summary", "update"))

    print(f"\n{GREEN}✓ Contexto actualizado correctamente.{NC}\n")


def parse_analysis(response: str) -> dict:
    """Parsea el JSON de respuesta del análisis."""
    # Limpiar markdown si viene envuelto
    clean = re.sub(r'```json\s*', '', response)
    clean = re.sub(r'```\s*', '', clean)
    clean = clean.strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Intentar extraer JSON del texto
        json_match = re.search(r'\{.*\}', clean, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except Exception:
                pass
    return {
        "summary": response[:200],
        "impact_level": "MEDIO",
        "affected_files": [],
        "cross_repo_impact": [],
        "context_updates": {},
        "alert_content": None
    }


def generate_alerts(loader, client: str, cross_impact: list, alert_content: str):
    """Genera ALERT.md en cada repo afectado."""
    config = loader.config
    client_data = config.get("clients", {}).get(client, {})
    repos = client_data.get("repos", {})

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    for item in cross_impact:
        affected_repo = item.get("repo") if isinstance(item, dict) else str(item)

        # Buscar la ruta del repo afectado
        repo_data = repos.get(affected_repo, {})
        repo_path = repo_data.get("path", "")

        if not repo_path or not os.path.exists(repo_path):
            print(f"  {YELLOW}⚠ No encontré la ruta de {affected_repo} — saltando{NC}")
            continue

        brain_dir = os.path.join(repo_path, ".cipher")
        os.makedirs(brain_dir, exist_ok=True)
        alert_path = os.path.join(brain_dir, "ALERT.md")

        final_content = f"""# ⚠️ ALERT — Impacto detectado
> Generado por cipher | {now}
> **Origen:** {loader.repo_name} | **Cliente:** {client}

{alert_content}

---
> Ejecutá `cipher status` para ver el contexto completo actualizado.
> Al resolver este impacto, ejecutá `cipher update` en este repo.
"""
        with open(alert_path, "w") as f:
            f.write(final_content)

        print(f"  {GREEN}✓ ALERT.md generado en {affected_repo}{NC}")

        # Notificar owner si está configurado
        owner = repo_data.get("owner", "")
        if owner:
            print(f"  {YELLOW}→ Notificar a: {owner}{NC}")


def commit_cipher(brain_dir: str, repo_name: str, summary: str):
    """Hace commit automático en cipher."""
    import subprocess
    msg = f"cipher: update context for {repo_name} — {summary[:60]}"
    try:
        subprocess.run(["git", "add", "."], cwd=brain_dir, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=brain_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  {GREEN}✓ Commit: {msg[:70]}{NC}")
        else:
            print(f"  {YELLOW}⚠ Commit falló: {result.stderr.strip()}{NC}")
    except Exception as e:
        print(f"  {YELLOW}⚠ No se pudo hacer commit: {e}{NC}")


def _generate_alert(source_repo: str, client: str, analysis: dict) -> str:
    """Genera contenido de ALERT.md desde el análisis."""
    cross = analysis.get("cross_repo_impact", [])
    reasons = []
    for item in cross:
        if isinstance(item, dict):
            reasons.append(f"- {item.get('reason', 'Ver diff en ' + source_repo)}")

    return f"""## Qué cambió en `{source_repo}`
{analysis.get('summary', 'Ver contexto actualizado')}

## Nivel de riesgo
{analysis.get('impact_level', 'MEDIO')}

## Qué revisar en este repo
{chr(10).join(reasons) if reasons else '- Revisar integración con ' + source_repo}

## Contexto completo
Ver `cipher/clients/{client}/{source_repo}/DEPENDENCIES.md`
"""


def _risk_color(level: str) -> str:
    colors = {
        "CRÍTICO": f"{RED}CRÍTICO{NC}",
        "ALTO": f"{YELLOW}ALTO{NC}",
        "MEDIO": f"{CYAN}MEDIO{NC}",
        "BAJO": f"{GREEN}BAJO{NC}",
    }
    return colors.get(level.upper(), level)
