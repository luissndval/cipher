"""
cipher analysis — Scanner
Escanea repositorios git y genera archivos de contexto estructurado con IA.
Extraído de commands/init para separar responsabilidades.
"""

import os
import re
import json
import time

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

CONTEXT_FILES = ["BUSINESS_RULES.md", "ARCHITECTURE.md", "DEPENDENCIES.md", "RISK_MATRIX.md"]

# Encabezado para marcar archivos generados por IA como borradores
_DRAFT_HEADER = (
    "> ⚠️ **[DRAFT]** Este archivo fue generado automáticamente por IA.\n"
    "> Revisá y validá antes de tratarlo como verdad estructural.\n\n"
)


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
    """Recopila archivos de configuración y código fuente clave del repo."""
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

    for fname in sorted(CONFIG_FILES):
        fpath = os.path.join(repo_path, fname)
        if os.path.exists(fpath):
            limit = MAX_PER_FILE * 2 if fname in ('README.md', 'CLAUDE.md') else MAX_PER_FILE
            add_file(fname, fpath, limit)

    PRIORITY_NAMES = {
        'main.py', 'app.py', 'server.py', 'index.py',
        'main.ts', 'main.js', 'index.ts', 'index.js', 'app.ts', 'app.js',
        'router.py', 'routes.py', 'urls.py',
        'models.py', 'schemas.py', 'database.py',
    }
    priority_files, other_files = [], []

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
            (priority_files if fname in PRIORITY_NAMES else other_files).append((rel_path, abs_path))

    for rel, abs_p in priority_files:
        add_file(rel, abs_p)
    for rel, abs_p in other_files:
        add_file(rel, abs_p)

    return info


def generate_context_files(
    provider, repo_name: str, repo_path: str,
    structure: str, repo_info: dict, output_dir: str
):
    """
    Genera los 4 archivos de contexto del repo en una sola llamada a la IA.
    Los archivos se marcan con encabezado DRAFT para indicar que son borradores.
    """
    files_content = "\n\n".join([
        f"=== {f['name']} ===\n{f['content']}"
        for f in repo_info.get("files", [])
    ])

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
                print(f"    [RETRY {attempt}/{MAX_RETRIES}] API no disponible, esperando {wait}s...")
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

        for filename in CONTEXT_FILES:
            content = parsed.get(filename, "")
            if not content:
                content = f"# {filename.replace('.md', '')} — {repo_name}\n\n> No generado. Completar manualmente.\n"
            # Agregar encabezado DRAFT a todos los archivos generados por IA
            final_content = _DRAFT_HEADER + content
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                f.write(final_content)
            print(f"    ✓ {filename}")

    except Exception as e:
        import traceback
        print(f"    [ERROR] Generación falló: {e}")
        print(f"    {traceback.format_exc()}")
        for filename in CONTEXT_FILES:
            content = _DRAFT_HEADER + f"# {filename.replace('.md', '')} — {repo_name}\n\n> Generación automática falló: {e}\n> Completar manualmente.\n"
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                f.write(content)


def detect_dependencies(provider, client_name: str, repo_configs: dict, repos: list) -> dict:
    """Detecta dependencias entre repos usando IA."""
    cipher_dir = os.environ.get("CIPHER_PATH", "")
    repo_summaries = []
    for repo_name, repo_path in repos:
        dep_file = os.path.join(cipher_dir, "clients", client_name, repo_name, "DEPENDENCIES.md")
        if os.path.exists(dep_file):
            with open(dep_file, encoding="utf-8", errors="replace") as f:
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
