"""
cipher init — Onboarding automático
Escanea repos .git en una carpeta, registra clientes y genera contexto con IA.
Usa Gemini como provider de análisis por defecto (mayor contexto, más eficiente).
"""

import os
import json
import subprocess
from pathlib import Path
from context_loader import ContextLoader
from providers import get_analysis_provider, save_provider_config

GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'


def cmd_init(args: list):
    scan_path = os.getcwd()

    for i, arg in enumerate(args):
        if arg == "--scan" and i + 1 < len(args):
            scan_path = args[i + 1]
        elif arg.startswith("--scan="):
            scan_path = arg.split("=", 1)[1]

    scan_path = os.path.abspath(scan_path)

    print(f"\n{BLUE}╔══════════════════════════════════════════╗")
    print(f"║          cipher init — Onboarding         ║")
    print(f"╚══════════════════════════════════════════╝{NC}\n")
    print(f"  Escaneando: {scan_path}\n")

    # 1. Encontrar cipher
    try:
        loader = ContextLoader()
    except FileNotFoundError as e:
        print(str(e))
        return

    # 2. Escanear repos .git
    repos = scan_git_repos(scan_path)

    if not repos:
        print(f"{RED}✗ No se encontraron repositorios .git en {scan_path}{NC}")
        return

    print(f"  Encontré {len(repos)} repositorio(s):\n")

    # 3. Seleccionar repos a registrar
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

    # 4. Nombre del cliente
    print()
    client_name = input(f"  ¿Nombre del cliente para estos repos? ").strip()
    if not client_name:
        client_name = os.path.basename(scan_path)
    client_name = client_name.lower().replace(" ", "-")

    # 5. Elegir provider de análisis (Gemini por defecto)
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
            print(f"  Ejecutá cipher init de nuevo y pegá tu API key.")
            return

    # 6. Analizar cada repo
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
            "consumed_by": []
        }
        print(f"  {GREEN}✓ {repo_name} — contexto generado{NC}")

    # 7. Detectar dependencias entre repos
    if len(selected_repos) > 1:
        print(f"\n  {YELLOW}Detectando dependencias entre repos...{NC}")
        repo_configs = detect_dependencies(provider, client_name, repo_configs, selected_repos)

    # 8. Guardar en config.json
    update_client_config(loader, client_name, repo_configs)

    # 9. Preparar .cipher/ en cada repo y actualizar .gitignore
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
    print(f"  {YELLOW}cipher claude{NC}   → iniciar sesión de desarrollo\n")


# ─── Escaneo de repos ─────────────────────────────────────────────────────────

def scan_git_repos(path: str) -> list:
    """Busca directorios con .git en la ruta dada (un nivel de profundidad)."""
    repos = []
    if os.path.exists(os.path.join(path, ".git")):
        repos.append(path)
    try:
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, ".git")):
                repos.append(item_path)
    except PermissionError:
        pass
    return repos


# ─── Lectura de repos ─────────────────────────────────────────────────────────

IGNORE_DIRS = {
    'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build',
    '.git', '.idea', '.vscode', 'coverage', '.next', '.nuxt', 'out',
    'uploads', 'migrations', 'alembic',
}

SOURCE_EXTENSIONS = {
    '.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.java', '.rb',
    '.rs', '.cs', '.php', '.vue', '.svelte',
}

CONFIG_FILES = {
    'package.json', 'requirements.txt', 'pyproject.toml', 'setup.py',
    'go.mod', 'Cargo.toml', 'pom.xml', 'Gemfile',
    'Dockerfile', 'docker-compose.yml',
    'README.md', 'CLAUDE.md', '.env.example',
}


def get_repo_structure(repo_path: str) -> str:
    """Árbol de directorios hasta 4 niveles."""
    lines = []
    try:
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in IGNORE_DIRS)
            level = root.replace(repo_path, '').count(os.sep)
            if level > 4:
                continue
            indent = '  ' * level
            lines.append(f"{indent}{os.path.basename(root)}/")
            subindent = '  ' * (level + 1)
            for file in sorted(files):
                lines.append(f"{subindent}{file}")
    except Exception:
        pass
    return "\n".join(lines[:300])


def get_repo_info(repo_path: str, max_total: int = 60_000) -> dict:
    """
    Recopila contexto real del repo:
    - Archivos de configuración completos
    - Código fuente de archivos clave (entry points, routers, models, etc.)
    """
    info = {"path": repo_path, "files": []}
    total_chars = 0
    MAX_PER_FILE = min(4_000, max_total // 10)

    def add_file(rel_path: str, abs_path: str, limit: int = MAX_PER_FILE):
        nonlocal total_chars
        if total_chars >= max_total:
            return
        try:
            with open(abs_path, encoding="utf-8", errors="ignore") as f:
                content = f.read(limit)
            if content.strip():
                info["files"].append({"name": rel_path, "content": content})
                total_chars += len(content)
        except Exception:
            pass

    # 1. Archivos de configuración en la raíz
    for fname in sorted(CONFIG_FILES):
        fpath = os.path.join(repo_path, fname)
        if os.path.exists(fpath):
            limit = MAX_PER_FILE * 2 if fname in ('README.md', 'CLAUDE.md') else MAX_PER_FILE
            add_file(fname, fpath, limit)

    # 2. Código fuente — prioridad por nombre de archivo
    PRIORITY_NAMES = {
        'main.py', 'app.py', 'server.py', 'index.py',
        'main.ts', 'main.js', 'index.ts', 'index.js', 'app.ts', 'app.js',
        'router.py', 'routes.py', 'urls.py',
        'models.py', 'schemas.py', 'database.py',
    }

    priority_files = []
    other_files = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in IGNORE_DIRS]
        if root.replace(repo_path, '').count(os.sep) > 4:
            continue
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in SOURCE_EXTENSIONS:
                continue
            abs_path = os.path.join(root, fname)
            rel_path = os.path.relpath(abs_path, repo_path).replace('\\', '/')
            if fname in PRIORITY_NAMES:
                priority_files.append((rel_path, abs_path))
            else:
                other_files.append((rel_path, abs_path))

    for rel, abs_p in priority_files:
        add_file(rel, abs_p)
    for rel, abs_p in other_files:
        add_file(rel, abs_p)

    return info


# ─── Generación de contexto ───────────────────────────────────────────────────

def generate_context_files(provider, repo_name: str, repo_path: str,
                            structure: str, repo_info: dict, output_dir: str):
    """Genera los 4 archivos de contexto del repo en una sola llamada a la IA."""
    import re
    import time

    files_content = "\n\n".join([
        f"=== {f['name']} ===\n{f['content']}"
        for f in repo_info.get("files", [])
    ])

    FILES = ["BUSINESS_RULES.md", "ARCHITECTURE.md", "DEPENDENCIES.md", "RISK_MATRIX.md"]

    prompt = f"""Analizá este repositorio y generá los 4 archivos de contexto.

Repo: {repo_name}

Estructura de directorios:
{structure}

Archivos clave:
{files_content}

Respondé EXACTAMENTE con este formato (sin nada antes ni después):

<<<FILE:BUSINESS_RULES.md>>>
[contenido: propósito del servicio, reglas de negocio BR-001..., restricciones, invariantes, glosario]

<<<FILE:ARCHITECTURE.md>>>
[contenido: stack tecnológico, arquitectura/capas, estructura de dirs, puntos de entrada, env vars requeridas]

<<<FILE:DEPENDENCIES.md>>>
[contenido: dependencias externas, endpoints que expone y consume, eventos de mensajería, advertencias críticas]

<<<FILE:RISK_MATRIX.md>>>
[contenido: componentes con nivel de riesgo BAJO/MEDIO/ALTO/CRÍTICO, criterio, reglas de escalamiento]"""

    MAX_RETRIES = 3
    response = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = provider.analyze_repo(prompt)
            break
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                wait = attempt * 15
                print(f"    {YELLOW}[RETRY {attempt}/{MAX_RETRIES}] API no disponible, esperando {wait}s...{NC}")
                time.sleep(wait)
            else:
                raise

    if response is None:
        raise RuntimeError("API no disponible después de varios intentos.")

    try:
        parsed = {}
        pattern = re.compile(r'<<<FILE:([\w.]+)>>>\n(.*?)(?=<<<FILE:|$)', re.DOTALL)
        for match in pattern.finditer(response):
            fname, content = match.group(1), match.group(2).strip()
            parsed[fname] = content

        for filename in FILES:
            content = parsed.get(filename, "")
            if not content:
                content = f"# {filename.replace('.md', '')} — {repo_name}\n\n> No generado. Completar manualmente.\n"
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    ✓ {filename}")

    except Exception as e:
        import traceback
        print(f"    {RED}[ERROR] Generación falló: {e}{NC}")
        print(f"    {traceback.format_exc()}")
        for filename in FILES:
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                f.write(f"# {filename.replace('.md', '')} — {repo_name}\n\n> Generación automática falló: {e}\n> Completar manualmente.\n")


def detect_dependencies(provider, client_name: str, repo_configs: dict, repos: list) -> dict:
    """Detecta dependencias entre repos usando IA."""
    repo_summaries = []
    for repo_name, repo_path in repos:
        dep_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "clients", client_name, repo_name, "DEPENDENCIES.md"
        )
        if os.path.exists(dep_file):
            with open(dep_file) as f:
                content = f.read()[:1000]
            repo_summaries.append(f"=== {repo_name} ===\n{content}")

    if not repo_summaries:
        return repo_configs

    prompt = f"""Analizá las dependencias de estos repos y determiná cuáles se consumen entre sí.

{chr(10).join(repo_summaries)}

Respondé SOLO con un JSON válido:
{{
  "dependencies": [
    {{"from": "nombre-repo", "to": "nombre-repo", "reason": "razón"}}
  ]
}}"""

    try:
        response = provider.analyze_repo(prompt)
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            for dep in data.get("dependencies", []):
                from_repo = dep.get("from")
                to_repo = dep.get("to")
                if from_repo in repo_configs and to_repo in repo_configs:
                    if to_repo not in repo_configs[from_repo]["depends_on"]:
                        repo_configs[from_repo]["depends_on"].append(to_repo)
                    if from_repo not in repo_configs[to_repo]["consumed_by"]:
                        repo_configs[to_repo]["consumed_by"].append(from_repo)
    except Exception:
        pass

    return repo_configs


# ─── Config ───────────────────────────────────────────────────────────────────

def update_client_config(loader: ContextLoader, client_name: str, repo_configs: dict):
    """Actualiza config.json con el nuevo cliente."""
    config = loader.config
    if "clients" not in config:
        config["clients"] = {}

    config["clients"][client_name] = {"repos": repo_configs}

    config_path = os.path.join(loader.cipher_dir, ".cipher", "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _configure_api_key(preferred: str):
    """Solicita y guarda la API key del provider de análisis."""
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
    """Agrega entradas de cipher al .gitignore del repo del cliente."""
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
