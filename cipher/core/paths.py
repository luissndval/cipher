"""
cipher core — Path utilities

Dos responsabilidades:
  1. Relative/absolute conversion — para persistencia portátil de paths internos.
  2. Repo path resolution — para no hardcodear paths absolutos de repos cliente.

Regla: todos los paths internos de cipher (.cipher/tasks, .cipher/sessions, etc.)
se guardan en JSON como relativos al cipher_dir. Se resuelven a absolutos al leer.
Esto hace los archivos portables entre developers y máquinas.

Para repos cliente, la resolución sigue este orden de prioridad:
  1. repo_data["path"] si está explícito (soporta ~ y $VAR)
  2. client_data["repos_base"] + repo_key  (sin path explícito)
  3. None si ninguno está disponible
"""

import os


def to_rel(abs_path: str, base_dir: str) -> str:
    """
    Convierte un path absoluto a relativo respecto a base_dir.
    Si están en drives distintos (Windows), retorna el path sin cambio.
    """
    if not abs_path:
        return abs_path
    try:
        rel = os.path.relpath(abs_path, base_dir)
        return rel.replace("\\", "/")
    except ValueError:
        # Windows: paths en drives distintos (ej: C: vs D:) no se pueden relativizar
        return abs_path.replace("\\", "/")


def to_abs(rel_or_abs: str, base_dir: str) -> str:
    """
    Reconstruye el path absoluto a partir de uno relativo a base_dir.
    Si ya es absoluto (retrocompatibilidad con JSONs viejos), lo devuelve tal cual.
    """
    if not rel_or_abs:
        return rel_or_abs
    if os.path.isabs(rel_or_abs):
        return rel_or_abs
    return os.path.normpath(os.path.join(base_dir, rel_or_abs))


def _expand(path: str) -> str:
    """Expande ~ y variables de entorno ($VAR o ${VAR}) en un path."""
    return os.path.normpath(os.path.expandvars(os.path.expanduser(path)))


def resolve_repo_path(client_data: dict, repo_key: str, repo_data: dict) -> str | None:
    """
    Resuelve el path absoluto de un repo cliente.
    Los paths los escribe install.py en config.local.json — no se hardcodean en config.json.

    Orden de resolución:
      1. repo_data["path"] si está definido (ya mergeado desde config.local.json por ContextLoader)
      2. client_data["repos_base"] + repo_key  (fallback si se configuró base)
      3. None si ninguno está disponible
    """
    if not isinstance(repo_data, dict):
        return None

    explicit = repo_data.get("path", "").strip()
    if explicit:
        return _expand(explicit)

    repos_base = client_data.get("repos_base", "").strip() if isinstance(client_data, dict) else ""
    if repos_base:
        return _expand(os.path.join(repos_base, repo_key))

    return None
