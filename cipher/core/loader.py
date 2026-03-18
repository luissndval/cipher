"""
cipher core — ContextLoader
Detecta el repo actual, resuelve cliente/proyecto y ensambla contexto.
"""

import os
import json
import subprocess
from datetime import datetime


class ContextLoader:
    def __init__(self, cipher_dir: str = None):
        self.cipher_dir = cipher_dir or self._find_cipher_dir()
        self.config = self._load_config()
        self.repo_name = self._detect_repo_name()
        self.repo_path = self._detect_repo_path()
        self.client = None
        self.project = None

    # ─── Setup ────────────────────────────────────────────────────────────────

    def _find_cipher_dir(self) -> str:
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
            if os.path.isdir(path) and os.path.exists(
                os.path.join(path, ".cipher", "config.json")
            ):
                return os.path.abspath(path)

        raise FileNotFoundError(
            "\033[31m✗ No se encontró cipher.\n"
            "  Asegurate de que cipher esté en el directorio padre,\n"
            "  o configurá CIPHER_PATH en tu entorno.\033[0m"
        )

    def _load_config(self) -> dict:
        config_path = os.path.join(self.cipher_dir, ".cipher", "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"✗ No se encontró config.json en {config_path}")
        with open(config_path) as f:
            return json.load(f)

    def _detect_repo_name(self) -> str:
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

    # ─── Project resolution ───────────────────────────────────────────────────

    def resolve_project(self) -> tuple:
        """
        Resuelve (client_name, project_name) para el repo actual.
        Retorna (None, None) si no hay match.
        """
        clients = self.config.get("clients", {})
        for client_name, client_data in clients.items():
            if not isinstance(client_data, dict):
                continue
            repos = client_data.get("repos", {})
            for repo_key, repo_data in repos.items():
                if not isinstance(repo_data, dict):
                    continue
                if repo_data.get("name") == self.repo_name or repo_key == self.repo_name:
                    self.client = client_name
                    self.project = repo_key
                    return client_name, repo_key
        return None, None

    # ─── Paths ────────────────────────────────────────────────────────────────

    def session_dir(self, client: str, project: str) -> str:
        return os.path.join(self.cipher_dir, ".cipher", "sessions", client, project)

    # ─── Context ──────────────────────────────────────────────────────────────

    def context_exists(self) -> bool:
        client, project = self.resolve_project()
        if not client:
            return False
        context_file = os.path.join(self.session_dir(client, project), "ACTIVE_CONTEXT.md")
        return os.path.exists(context_file)

    def assemble_context(self, client: str, project: str, mode: str = "summary") -> str:
        """
        Ensambla ACTIVE_CONTEXT.md en capas: GLOBAL → CLIENTE → PROYECTO.
        Los archivos generados por IA se marcan como [DRAFT].
        """
        lines = []
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        lines.append("<!-- GENERADO POR cipher — NO EDITAR MANUALMENTE -->")
        lines.append(f"<!-- Repo: {self.repo_name} | Cliente: {client} | Proyecto: {project} -->")
        lines.append(f"<!-- Fecha: {now} | Modo: {mode} -->")
        lines.append("")

        # CAPA GLOBAL
        lines.append("---")
        lines.append("## CAPA GLOBAL — Reglas de la consultora")
        lines.append("")
        for fname in ["CONVENTIONS.md", "WORKFLOW.md", "AGENT.md"]:
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

        # CAPA PROYECTO
        project_dir = os.path.join(client_dir, project) if os.path.exists(client_dir) else None
        if project_dir and os.path.exists(project_dir):
            lines.append("---")
            lines.append(f"## CAPA PROYECTO — {project} ⚠️ [DRAFT — generado por IA, no validado estructuralmente]")
            lines.append("")
            for fname in ["BUSINESS_RULES.md", "ARCHITECTURE.md", "DEPENDENCIES.md", "RISK_MATRIX.md"]:
                fpath = os.path.join(project_dir, fname)
                if os.path.exists(fpath):
                    lines.append(self._read_file(fpath, mode))
                    lines.append("")

        # Índice on-demand
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
        if mode == "summary":
            summary_path = path.replace(".md", ".summary.md")
            if os.path.exists(summary_path):
                with open(summary_path, encoding="utf-8", errors="ignore") as f:
                    return f.read()
            with open(path, encoding="utf-8", errors="ignore") as f:
                file_lines = f.readlines()
            content = "".join(file_lines[:30])
            if len(file_lines) > 30:
                content += f"\n> [TRUNCADO] Archivo completo: {path}\n"
            return content
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()

    def save_context(self, content: str, client: str = None, project: str = None) -> str:
        client = client or self.client
        project = project or self.project
        session_dir = self.session_dir(client, project)
        os.makedirs(session_dir, exist_ok=True)
        output_path = os.path.join(session_dir, "ACTIVE_CONTEXT.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    # ─── Git helpers ──────────────────────────────────────────────────────────

    def get_git_diff(self) -> str:
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
        try:
            result = subprocess.run(
                ["git", "log", f"-{n}", "--oneline"],
                capture_output=True, text=True, cwd=self.repo_path
            )
            return result.stdout.strip()
        except Exception:
            return ""
