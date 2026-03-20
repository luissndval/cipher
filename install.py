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
    config_local_path = os.path.join(HERE, ".cipher", "config.local.json")
    os.makedirs(os.path.dirname(config_local_path), exist_ok=True)

    # Cargar o crear config.local.json
    if os.path.exists(config_local_path):
        with open(config_local_path, encoding="utf-8") as f:
            local_cfg = json.load(f)
        ok("config.local.json existente — actualizando paths...")
    else:
        local_cfg = {
            "anthropic": {"api_key": "", "model": "claude-sonnet-4-6"},
            "google":    {"api_key": "", "model": "gemini-2.5-flash"},
        }
        ok("config.local.json creado — agregá tus API keys en .cipher/config.local.json")

    # Leer clientes registrados en config.json y preguntar paths
    config_json_path = os.path.join(HERE, ".cipher", "config.json")
    if os.path.exists(config_json_path):
        with open(config_json_path, encoding="utf-8") as f:
            base_cfg = json.load(f)
        _configure_repo_paths(base_cfg, local_cfg)

    with open(config_local_path, "w", encoding="utf-8") as f:
        json.dump(local_cfg, f, indent=2, ensure_ascii=False)
    ok("config.local.json guardado")

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


def _configure_repo_paths(base_cfg: dict, local_cfg: dict):
    """
    Para cada cliente en config.json:
      1. Pregunta la carpeta base donde viven sus repos.
      2. Para repos que ya existen ahí → registra el path.
      3. Para repos que no existen pero tienen git_url → clona automáticamente (SSH).
      4. Para repos sin git_url y sin path → avisa que hay que configurarlos manualmente.
    Los paths se guardan en config.local.json (gitignoreado).
    """
    clients = base_cfg.get("clients", {})
    if not clients:
        return

    print(f"\n  {YELLOW}Configurando paths de repos cliente...{NC}")
    print(f"  (Los paths se guardan en config.local.json — no se commitean)\n")

    local_clients = local_cfg.setdefault("clients", {})

    for client_name, client_data in clients.items():
        if not isinstance(client_data, dict):
            continue
        repos = client_data.get("repos", {})
        if not repos:
            continue

        print(f"  {BLUE}Cliente: {client_name}{NC}  ({len(repos)} repo(s): {', '.join(repos.keys())})")

        local_client = local_clients.setdefault(client_name, {})
        local_repos = local_client.setdefault("repos", {})

        # Detectar carpeta base actual desde paths ya registrados
        existing_paths = [
            local_repos.get(rk, {}).get("path", "")
            for rk in repos
            if local_repos.get(rk, {}).get("path", "")
        ]
        default_base = os.path.dirname(existing_paths[0]) if existing_paths else ""

        base_hint = f" [{default_base}]" if default_base else ""
        answer = input(
            f"  ¿Carpeta base donde clonar/encontrar los repos de '{client_name}'?{base_hint}\n"
            f"  (Enter para usar default / 'skip' para omitir): "
        ).strip()

        if answer.lower() == "skip":
            print(f"  {YELLOW}  → {client_name} omitido.{NC}\n")
            continue

        if not answer and default_base:
            answer = default_base

        if not answer:
            print(f"  {YELLOW}  → Sin carpeta base — omitido.{NC}\n")
            continue

        repos_base = os.path.normpath(os.path.expanduser(answer))
        os.makedirs(repos_base, exist_ok=True)

        for repo_key, repo_data in repos.items():
            if not isinstance(repo_data, dict):
                continue
            rpath = os.path.join(repos_base, repo_key)

            if os.path.isdir(rpath):
                ok(f"[{repo_key}] encontrado → {rpath}")
                local_repos.setdefault(repo_key, {})["path"] = rpath
                continue

            # No existe localmente — intentar clonar si hay git_url
            git_url = repo_data.get("git_url", "").strip()
            if git_url:
                print(f"  Clonando {CYAN}{repo_key}{NC} desde {git_url} ...")
                result = subprocess.run(
                    ["git", "clone", git_url, rpath],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    ok(f"[{repo_key}] clonado → {rpath}")
                    local_repos.setdefault(repo_key, {})["path"] = rpath
                else:
                    err(f"[{repo_key}] Error al clonar: {result.stderr.strip()}")
                    warn(f"  Verificá que tu SSH key tenga acceso a {git_url}")
            else:
                warn(f"[{repo_key}] no encontrado y sin git_url — configurá el path manualmente en config.local.json")

        print()


if __name__ == "__main__":
    main()
