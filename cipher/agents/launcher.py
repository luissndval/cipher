"""
cipher agents — Launcher
Lanza el agente de codificación con contexto inyectado via CLAUDE.md temporal.
"""

import os
import subprocess


def launch_agent(agent: str, context_path: str, task_path: str, repo_path: str):
    """Despacha al agente correcto."""
    with open(context_path, encoding="utf-8") as f:
        context_content = f.read()
    with open(task_path, encoding="utf-8") as f:
        task_content = f.read()

    if agent == "claude":
        _launch_claude(context_content, task_content, repo_path)
    else:
        print(f"\033[31m✗ Agente no soportado: {agent}\033[0m")
        print("  Agentes disponibles: claude")


def _launch_claude(context: str, task: str, repo_path: str):
    """
    Lanza Claude Code inyectando contexto via CLAUDE.md temporal.
    El archivo se restaura o elimina automáticamente al salir.
    """
    if not _check_command("claude"):
        print("\033[31m✗ Claude Code no está instalado.\033[0m")
        print("  Instalalo con: npm install -g @anthropic-ai/claude-code")
        return

    claude_md_path = os.path.join(repo_path, "CLAUDE.md")
    claude_md_existed = os.path.exists(claude_md_path)
    original_content = None
    if claude_md_existed:
        with open(claude_md_path, encoding="utf-8", errors="ignore") as f:
            original_content = f.read()

    injected_content = f"""# Contexto cipher — SESIÓN ACTIVA (se borra al salir)

## TAREA ACTUAL
{task}

## CONTEXTO DEL PROYECTO
{context}
"""
    try:
        with open(claude_md_path, "w", encoding="utf-8") as f:
            f.write(injected_content)
        print(f"\033[0;32m  ✓ Contexto inyectado (CLAUDE.md temporal)\033[0m")
        print(f"  Iniciando Claude Code en {repo_path}...\n")
        initial_prompt = (
            "Leé el CLAUDE.md completo. "
            "Empezá por el PASO 1: creá la branch indicada en la sección TAREA ACTUAL. "
            "Luego implementá lo requerido siguiendo los pasos en orden. "
            "Al terminar, hacé commit, push y creá el PR según las instrucciones."
        )
        subprocess.run(["claude", initial_prompt], cwd=repo_path)
    finally:
        if claude_md_existed and original_content is not None:
            with open(claude_md_path, "w", encoding="utf-8") as f:
                f.write(original_content)
        elif os.path.exists(claude_md_path):
            os.remove(claude_md_path)
        print(f"\033[0;32m  ✓ CLAUDE.md eliminado del repo cliente\033[0m")


def _check_command(cmd: str) -> bool:
    try:
        result = subprocess.run(
            ["where", cmd] if os.name == "nt" else ["which", cmd],
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False
