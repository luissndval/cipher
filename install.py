#!/usr/bin/env python3
"""
cipheria — install.py
Instalación universal: Windows (PowerShell/CMD), Git Bash, Linux, macOS.
Uso: python install.py
"""

import sys
import os

# Fix encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import subprocess
import shutil
import json
import platform

HERE = os.path.dirname(os.path.abspath(__file__))
BIN  = os.path.join(HERE, "bin")
IS_WIN = sys.platform == "win32"

GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
BLUE   = "\033[0;34m"
NC     = "\033[0m"

def c(color, text):
    return f"{color}{text}{NC}"

def ok(msg):   print(f"  {GREEN}+{NC} {msg}")
def warn(msg): print(f"  {YELLOW}!{NC} {msg}")
def err(msg):  print(f"  {RED}!{NC} {msg}")
def step(msg): print(f"\n{YELLOW}> {msg}{NC}")


def main():
    print(f"""
{BLUE}╔══════════════════════════════════════════╗
║       cipheria — Instalación             ║
║   Memoria persistente para agentes IA    ║
╚══════════════════════════════════════════╝{NC}
""")

    # ── 1. Python ────────────────────────────────────────────────────────────
    step("Verificando Python...")
    ok(f"Python {sys.version.split()[0]}")

    # ── 2. Dependencias ──────────────────────────────────────────────────────
    step("Instalando dependencias Python...")
    req = os.path.join(HERE, "requirements.txt")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", req],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err(f"pip falló:\n{result.stderr}")
        sys.exit(1)
    ok("Dependencias instaladas")

    # ── 3. Claude Code ───────────────────────────────────────────────────────
    step("Verificando Claude Code...")
    if shutil.which("claude"):
        ok("Claude Code ya instalado")
    elif shutil.which("npm"):
        warn("Instalando Claude Code via npm...")
        r = subprocess.run(["npm", "install", "-g", "@anthropic-ai/claude-code"],
                           capture_output=True)
        if r.returncode == 0:
            ok("Claude Code instalado")
        else:
            warn("Claude Code falló. Instalalo manualmente: npm install -g @anthropic-ai/claude-code")
    else:
        warn("npm no encontrado — instalá Claude Code manualmente: npm install -g @anthropic-ai/claude-code")

    # ── 4. Scripts de comando ────────────────────────────────────────────────
    step("Registrando comando cipheria...")
    os.makedirs(BIN, exist_ok=True)

    # Bash script (Linux / macOS / Git Bash)
    bash_script = os.path.join(BIN, "cipheria")
    with open(bash_script, "w", newline="\n") as f:
        f.write(f'#!/usr/bin/env bash\n')
        f.write(f'export CIPHER_PATH="{HERE}"\n')
        f.write(f'python3 "{HERE}/cipher/main.py" "$@"\n')
    try:
        os.chmod(bash_script, 0o755)
    except Exception:
        pass
    ok("bin/cipheria creado (bash)")

    # CMD / PowerShell wrapper
    cmd_script = os.path.join(BIN, "cipheria.cmd")
    with open(cmd_script, "w", newline="\r\n") as f:
        f.write(f'@echo off\n')
        f.write(f'set CIPHER_PATH={HERE}\n')
        f.write(f'"{sys.executable}" "{HERE}\\cipher\\main.py" %*\n')
    ok("bin/cipheria.cmd creado (PowerShell/CMD)")

    # ── 5. PATH ──────────────────────────────────────────────────────────────
    step("Configurando PATH...")

    if IS_WIN:
        _add_to_path_windows(BIN)
    else:
        _add_to_path_unix(BIN)

    # ── 6. config.local.json ─────────────────────────────────────────────────
    step("Configurando config.local.json...")
    config_local = os.path.join(HERE, ".cipher", "config.local.json")
    config_example = os.path.join(HERE, ".cipher", "config.local.example.json")
    if not os.path.exists(config_local):
        if os.path.exists(config_example):
            shutil.copy(config_example, config_local)
        else:
            os.makedirs(os.path.dirname(config_local), exist_ok=True)
            with open(config_local, "w") as f:
                json.dump({
                    "anthropic": {"api_key": "", "model": "claude-sonnet-4-6"},
                    "google":    {"api_key": "", "model": "gemini-2.5-flash"},
                }, f, indent=2)
        ok("config.local.json creado — agregá tus API keys")
    else:
        ok("config.local.json ya existe")

    # ── 7. Resumen ───────────────────────────────────────────────────────────
    print(f"""
{BLUE}╔══════════════════════════════════════════╗
║        + Instalación completa            ║
╚══════════════════════════════════════════╝{NC}

  {YELLOW}Reiniciá tu terminal{NC} para que cipheria quede disponible.

  Luego:
    {YELLOW}cipheria init{NC}     — registra el proyecto y genera contexto
    {YELLOW}cipheria index{NC}    — indexa el repo para análisis de impacto
    {YELLOW}cipheria impact{NC}   — modo interactivo de impacto
    {YELLOW}cipheria status{NC}   — estado del contexto actual

  {BLUE}Configurá tus API keys en .cipher/config.local.json{NC}
""")


def _add_to_path_windows(bin_dir: str):
    """Agrega bin_dir al PATH del usuario en Windows (permanente)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0, winreg.KEY_READ | winreg.KEY_WRITE,
        )
        try:
            current, _ = winreg.QueryValueEx(key, "PATH")
        except FileNotFoundError:
            current = ""

        if bin_dir.lower() not in current.lower():
            new_path = f"{current};{bin_dir}" if current else bin_dir
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            # Notificar al sistema del cambio de environment
            import ctypes
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x001A, 0, "Environment")
            ok(f"PATH actualizado permanentemente ({bin_dir})")
            print(f"\n  Para aplicarlo {YELLOW}sin reiniciar{NC} PowerShell, ejecutá:")
            print(f'  {YELLOW}$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","Machine"){NC}\n')
        else:
            ok("PATH ya contiene el directorio bin/")
    except Exception as e:
        warn(f"No se pudo modificar el PATH automáticamente: {e}")
        print(f"\n  Ejecutá esto en PowerShell para agregar al PATH:")
        print(f'  {YELLOW}[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";{bin_dir}", "User"){NC}\n')


def _add_to_path_unix(bin_dir: str):
    """Agrega bin_dir al PATH en el shell RC del usuario."""
    rc_candidates = [
        os.path.expanduser("~/.zshrc"),
        os.path.expanduser("~/.bashrc"),
        os.path.expanduser("~/.bash_profile"),
    ]
    rc = next((f for f in rc_candidates if os.path.exists(f)), None)
    export_line = f'export PATH="{bin_dir}:$PATH"'

    if rc:
        with open(rc) as f:
            content = f.read()
        if bin_dir not in content:
            with open(rc, "a") as f:
                f.write(f"\n# cipheria CLI\n{export_line}\n")
            ok(f"PATH actualizado en {rc}")
        else:
            ok("PATH ya configurado")
    else:
        warn(f"No se encontró shell RC. Agregá manualmente a tu perfil:\n  {export_line}")


if __name__ == "__main__":
    main()
