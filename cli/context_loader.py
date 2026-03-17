"""
cipher — ContextLoader
Detecta el repo actual, resuelve el cliente/proyecto y ensambla el contexto.
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime


class ContextLoader:
    def __init__(self, cipher_dir: str = None):
        self.cipher_dir = cipher_dir or self._find_cipher_dir()
        self.config = self._load_config()
        self.repo_name = self._detect_repo_name()
        self.repo_path = self._detect_repo_path()
        self.client = None
        self.project = None

    def _find_cipher_dir(self) -> str:
        """Busca el directorio cipher desde el CWD hacia arriba."""
        candidates = [
            os.path.join(os.getcwd(), "cipher"),
            os.path.join(os.getcwd(), "..", "cipher"),
            os.path.join(os.getcwd(), "..", "..", "cipher"),
            os.path.expanduser("~/.cipher"),
        ]
        env_path = os.environ.get("CIPHER_PATH")
        if env_path:
            candidates.insert(0, env_path)

        for path in candidates:
            if os.path.isdir(path) and os.path.exists(os.path.join(path, ".cipher", "config.json")):
                return os.path.abspath(path)

        raise FileNotFoundError(
            "\033[31m✗ No se encontró cipher.\n"
            "  Asegurate de que cipher esté en el directorio padre,\n"
            "  o configurá CIPHER_PATH en tu entorno.\033[0m"
        )

    def _load_config(self) -> dict:
        """Carga config.json del repo cipher."""
        config_path = os.path.join(self.cipher_dir, ".cipher", "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"✗ No se encontró config.json en {config_path}")
        with open(config_path) as f:
            return json.load(f)

    def _detect_repo_name(self) -> str:
        """Detecta el nombre del repo actual via git."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, cwd=os.getcwd()
            )
            if result.returncode == 0:
                return os.path.basename(result.stdout.strip())
        except Exception:
            pass
        return os.path.basename(os.getcwd())

    def _detect_repo_path(self) -> str:
        """Detecta la ruta raíz del repo actual."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, cwd=os.getcwd()
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return os.getcwd()

    def resolve_project(self) -> tuple:
        """
        Resuelve el cliente y proyecto para el repo actual.
        Retorna (client_name, project_name) o (None, None) si no hay match.
        """
        clients = self.config.get("clients", {})
        for client_name, client_data in clients.items():
            repos = client_data.get("repos", {})
            for repo_key, repo_data in repos.items():
                if repo_data.get("name") == self.repo_name or repo_key == self.repo_name:
                    self.client = client_name
                    self.project = repo_key
                    return client_name, repo_key
        return None, None

    def session_dir(self, client: str, project: str) -> str:
        """Directorio de sesión dentro del proyecto cipher (nunca en el repo cliente)."""
        return os.path.join(self.cipher_dir, ".cipher", "sessions", client, project)

    def context_exists(self) -> bool:
        """Verifica si ya existe contexto generado para este repo."""
        client, project = self.resolve_project()
        if not client:
            return False
        context_file = os.path.join(self.session_dir(client, project), "ACTIVE_CONTEXT.md")
        return os.path.exists(context_file)

    def assemble_context(self, client: str, project: str, mode: str = "summary") -> str:
        """
        Ensambla ACTIVE_CONTEXT.md en el orden de capas:
        GLOBAL → CLIENTE → PROYECTO
        """
        lines = []
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        lines.append(f"<!-- GENERADO POR cipher — NO EDITAR MANUALMENTE -->")
        lines.append(f"<!-- Repo: {self.repo_name} | Cliente: {client} | Proyecto: {project} -->")
        lines.append(f"<!-- Fecha: {now} | Modo: {mode} -->")
        lines.append("")

        # CAPA GLOBAL
        lines.append("---")
        lines.append("## CAPA GLOBAL — Reglas de la consultora")
        lines.append("")
        global_files = ["CONVENTIONS.md", "WORKFLOW.md", "AGENT.md"]
        for fname in global_files:
            fpath = os.path.join(self.cipher_dir, "global", fname)
            if os.path.exists(fpath):
                lines.append(self._read_file(fpath, mode))
                lines.append("")

        # CAPA CLIENTE
        client_dir = os.path.join(self.cipher_dir, "clients", client)
        if os.path.exists(client_dir):
            lines.append("---")
            lines.append(f"## CAPA CLIENTE — {client}")
            lines.append("")
            for fname in ["BUSINESS_RULES.md", "ARCHITECTURE.md"]:
                fpath = os.path.join(client_dir, fname)
                if os.path.exists(fpath):
                    lines.append(self._read_file(fpath, mode))
                    lines.append("")

        # CAPA PROYECTO — solo archivos generados por cipher init
        project_dir = os.path.join(client_dir, project) if os.path.exists(client_dir) else None
        if project_dir and os.path.exists(project_dir):
            lines.append("---")
            lines.append(f"## CAPA PROYECTO — {project}")
            lines.append("")
            for fname in ["BUSINESS_RULES.md", "ARCHITECTURE.md", "DEPENDENCIES.md", "RISK_MATRIX.md"]:
                fpath = os.path.join(project_dir, fname)
                if os.path.exists(fpath):
                    lines.append(self._read_file(fpath, mode))
                    lines.append("")

        # ÍNDICE on-demand
        lines.append("---")
        lines.append("## ARCHIVOS DISPONIBLES ON-DEMAND")
        lines.append("")
        lines.append("Cargá el archivo completo si el paso actual lo requiere:")
        if project_dir and os.path.exists(project_dir):
            for fname in ["ARCHITECTURE.md", "DEPENDENCIES.md", "RISK_MATRIX.md"]:
                fpath = os.path.join(project_dir, fname)
                if os.path.exists(fpath):
                    lines.append(f"- `{fpath}`")

        return "\n".join(lines)

    def _read_file(self, path: str, mode: str) -> str:
        """Lee un archivo de contexto según el modo (summary o full)."""
        if mode == "summary":
            summary_path = path.replace(".md", ".summary.md")
            if os.path.exists(summary_path):
                with open(summary_path, encoding="utf-8", errors="ignore") as f:
                    return f.read()
            with open(path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            content = "".join(lines[:30])
            if len(lines) > 30:
                content += f"\n> [TRUNCADO] Archivo completo: {path}\n"
            return content
        else:
            with open(path, encoding="utf-8", errors="ignore") as f:
                return f.read()

    def save_context(self, content: str, client: str = None, project: str = None) -> str:
        """Guarda ACTIVE_CONTEXT.md en el proyecto cipher (no en el repo cliente)."""
        client = client or self.client
        project = project or self.project
        session_dir = self.session_dir(client, project)
        os.makedirs(session_dir, exist_ok=True)
        output_path = os.path.join(session_dir, "ACTIVE_CONTEXT.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    def get_git_diff(self) -> str:
        """Obtiene el git diff del repo actual (staged + unstaged)."""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True, text=True, cwd=self.repo_path
            )
            diff = result.stdout.strip()
            if not diff:
                result = subprocess.run(
                    ["git", "diff", "--cached"],
                    capture_output=True, text=True, cwd=self.repo_path
                )
                diff = result.stdout.strip()
            return diff
        except Exception:
            return ""

    def get_recent_commits(self, n: int = 5) -> str:
        """Obtiene los últimos N commits del repo."""
        try:
            result = subprocess.run(
                ["git", "log", f"-{n}", "--oneline"],
                capture_output=True, text=True, cwd=self.repo_path
            )
            return result.stdout.strip()
        except Exception:
            return ""
