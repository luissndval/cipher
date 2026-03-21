"""
cipher update — Actualiza el contexto después de un cambio.
Detecta git diff, analiza con IA y propone cambios al contexto.
"""

import os
import re
import json
import subprocess
from datetime import datetime

from cipher.core.loader import ContextLoader
from cipher.analysis.providers import get_analysis_provider

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
NC     = '\033[0m'


def cmd_update(args: list):
    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║     cipheria update — Actualizar contexto  ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")

    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    client, project = loader.resolve_project()
    if not client:
        print(f"{RED}✗ Este repo no está registrado en cipheria.{NC}")
        print(f"  Ejecutá 'cipheria init' primero.")
        return

    print(f"  Repo    : {CYAN}{loader.repo_name}{NC}")
    print(f"  Cliente : {CYAN}{client}{NC}")

    diff = loader.get_git_diff()
    if not diff:
        recent = loader.get_recent_commits(3)
        print(f"\n  {YELLOW}No hay cambios pendientes en git.{NC}")
        if recent:
            print("  Últimos commits:\n")
            for line in recent.split("\n"):
                print(f"    {line}")
        answer = input("\n  ¿Analizar el último commit de todas formas? [s/N]: ").strip().lower()
        if answer not in ["s", "si", "y"]:
            print(f"  {YELLOW}Sin cambios para analizar.{NC}")
            return
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"],
            capture_output=True, text=True, cwd=loader.repo_path
        )
        diff = result.stdout.strip()

    diff_lines = diff.count('\n')
    files_changed = len([l for l in diff.split('\n') if l.startswith('diff --git')])
    print(f"\n  Cambios detectados: {files_changed} archivo(s), ~{diff_lines} líneas\n")

    # Leer task-agent.md si existe (desde session_dir en cipher, no en el repo cliente)
    session_dir = loader.session_dir(client, project)
    task_path = os.path.join(session_dir, "task-agent.md")
    task_content = ""
    if os.path.exists(task_path):
        with open(task_path) as f:
            task_content = f.read()
        print(f"  {GREEN}✓ task-agent.md encontrado{NC}")
    else:
        print(f"  {YELLOW}⚠ No encontré task-agent.md{NC}")
        task_content = input("  Describí brevemente qué cambió: ").strip()

    print(f"\n  {YELLOW}¿Qué provider usar para analizar el cambio?{NC}")
    print(f"    1. Gemini  {CYAN}(recomendado){NC}")
    print(f"    2. Claude")
    choice = input("  [1/2, Enter=Gemini]: ").strip()
    preferred = "claude" if choice == "2" else "gemini"

    provider = get_analysis_provider(preferred)
    if not provider.is_configured():
        print(f"{RED}✗ API key no configurada para {preferred}.{NC}")
        return

    print(f"\n  {YELLOW}Analizando cambios con {provider.name}...{NC}")
    system_prompt = (
        "Sos un arquitecto de software que analiza cambios en repositorios. "
        "Determiná qué cambió arquitecturalmente y proponé actualizaciones al contexto. "
        "Respondés siempre en JSON válido, sin markdown, sin explicaciones fuera del JSON."
    )

    try:
        response = provider.analyze_diff(system_prompt, diff, task_content)
        analysis = _parse_analysis(response)
    except Exception as e:
        print(f"{RED}✗ Error al analizar: {e}{NC}")
        return

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
        print("\n  Archivos de contexto a actualizar:")
        for fname in context_updates.keys():
            print(f"    → {fname}")

    print(f"\n{'─' * 50}\n")

    answer = input("  ¿Actualizo el contexto en cipher? [S/n]: ").strip().lower()
    if answer not in ["", "s", "si", "y"]:
        print(f"  {YELLOW}Actualización cancelada.{NC}")
        return

    client_project_dir = os.path.join(loader.cipher_dir, "clients", client, project)
    os.makedirs(client_project_dir, exist_ok=True)

    for filename, new_content in context_updates.items():
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
        file_path = os.path.join(client_project_dir, filename)
        with open(file_path, "w") as f:
            f.write(new_content)
        print(f"  {GREEN}✓ Actualizado: {filename}{NC}")

    if cross_impact:
        alert_content = analysis.get("alert_content") or _generate_alert(
            loader.repo_name, client, analysis
        )
        answer2 = input("\n  ¿Genero ALERT.md en los repos afectados? [S/n]: ").strip().lower()
        if answer2 in ["", "s", "si", "y"]:
            _generate_alerts(loader, client, cross_impact, alert_content)

    context = loader.assemble_context(client, project, mode="summary")
    loader.save_context(context)
    print(f"  {GREEN}✓ ACTIVE_CONTEXT.md regenerado{NC}")

    answer3 = input("\n  ¿Hacer commit en cipher? [S/n]: ").strip().lower()
    if answer3 in ["", "s", "si", "y"]:
        _commit_cipher(loader.cipher_dir, loader.repo_name, analysis.get("summary", "update"))

    print(f"\n{GREEN}✓ Contexto actualizado correctamente.{NC}\n")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_analysis(response: str) -> dict:
    clean = re.sub(r'```json\s*', '', response)
    clean = re.sub(r'```\s*', '', clean).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
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
        "alert_content": None,
    }


def _generate_alerts(loader, client: str, cross_impact: list, alert_content: str):
    repos = loader.config.get("clients", {}).get(client, {}).get("repos", {})
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for item in cross_impact:
        affected_repo = item.get("repo") if isinstance(item, dict) else str(item)
        repo_data = repos.get(affected_repo, {})
        repo_path = repo_data.get("path", "")
        if not repo_path or not os.path.exists(repo_path):
            print(f"  {YELLOW}⚠ No encontré la ruta de {affected_repo} — saltando{NC}")
            continue
        brain_dir = os.path.join(repo_path, ".cipher")
        os.makedirs(brain_dir, exist_ok=True)
        alert_path = os.path.join(brain_dir, "ALERT.md")
        with open(alert_path, "w") as f:
            f.write(
                f"# ⚠️ ALERT — Impacto detectado\n"
                f"> Generado por cipheria | {now}\n"
                f"> **Origen:** {loader.repo_name} | **Cliente:** {client}\n\n"
                f"{alert_content}\n\n---\n"
                f"> Ejecutá `cipheria status` para ver el contexto completo actualizado.\n"
                f"> Al resolver este impacto, ejecutá `cipheria update` en este repo.\n"
            )
        print(f"  {GREEN}✓ ALERT.md generado en {affected_repo}{NC}")
        owner = repo_data.get("owner", "")
        if owner:
            print(f"  {YELLOW}→ Notificar a: {owner}{NC}")


def _commit_cipher(brain_dir: str, repo_name: str, summary: str):
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
    cross = analysis.get("cross_repo_impact", [])
    reasons = [
        f"- {item.get('reason', 'Ver diff en ' + source_repo)}"
        for item in cross if isinstance(item, dict)
    ]
    return (
        f"## Qué cambió en `{source_repo}`\n"
        f"{analysis.get('summary', 'Ver contexto actualizado')}\n\n"
        f"## Nivel de riesgo\n{analysis.get('impact_level', 'MEDIO')}\n\n"
        f"## Qué revisar en este repo\n"
        f"{chr(10).join(reasons) if reasons else '- Revisar integración con ' + source_repo}\n\n"
        f"## Contexto completo\n"
        f"Ver `cipher/clients/{client}/{source_repo}/DEPENDENCIES.md`\n"
    )


def _risk_color(level: str) -> str:
    colors = {
        "CRÍTICO": f"{RED}CRÍTICO{NC}",
        "ALTO":    f"{YELLOW}ALTO{NC}",
        "MEDIO":   f"{CYAN}MEDIO{NC}",
        "BAJO":    f"{GREEN}BAJO{NC}",
    }
    return colors.get(level.upper(), level)
