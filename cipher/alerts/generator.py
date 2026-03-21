"""
cipher alerts — AlertGenerator

Genera alert-{type}-{id}.md usando Gemini para análisis de impacto cross-repo.
Se activa durante `cipheria task` después del context pack.

Output: .cipher/alerts/<client>/alert-{TYPE}-{task_id}.md
"""

import os


class AlertGenerator:
    MAX_FILE_CHARS = 4_000   # chars por archivo fuente enviados a Gemini
    MAX_CONSUMERS  = 8       # max archivos consumidores por repo externo

    def __init__(
        self,
        task,
        impact_entries: list,
        repo_path: str,
        client_name: str,
        cipher_dir: str,
        config: dict,
    ):
        self.task           = task
        self.impact_entries = impact_entries   # list[ImpactEntry]
        self.repo_path      = repo_path
        self.client_name    = client_name
        self.cipher_dir     = cipher_dir
        self.config         = config

    def generate(self, provider) -> str:
        """Llama a Gemini y retorna el path del alert generado."""
        prompt = self._build_prompt()
        content = provider.chat(
            system_prompt=(
                "Sos un arquitecto de software senior especializado en análisis de impacto. "
                "Tu trabajo es analizar cambios en código y generar matrices de riesgo "
                "estructuradas en markdown. "
                "Respondés SOLO con el contenido del archivo markdown, "
                "sin explicaciones adicionales ni bloques de código externos."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        return self._save(content)

    # ─── Construcción del prompt ───────────────────────────────────────────────

    def _build_prompt(self) -> str:
        task = self.task
        lines = [
            f"Generá un alert de impacto para la siguiente task:",
            f"",
            f"**Task ID:** {task.type}-{task.task_id}",
            f"**Título:** {task.title}",
            f"**Descripción:** {task.description or '—'}",
            f"**Repo origen:** {task.repo}",
            f"",
        ]

        # Archivos target
        lines += ["## Archivos a modificar (objetivo de la task)", ""]
        for f in (task.target_files or []):
            lines.append(f"- `{f}`")
        lines.append("")

        # Impact set interno
        lines += ["## Impact set interno (grafo de imports)", ""]
        if self.impact_entries:
            for entry in self.impact_entries:
                via = f" — via {' → '.join(entry.via[-2:])}" if entry.via else ""
                lines.append(f"- depth {entry.depth}: `{entry.file_path}`{via}")
        else:
            lines.append("- Sin dependientes internos detectados.")
        lines.append("")

        # Código fuente de archivos relevantes
        lines += ["## Código fuente de archivos relevantes", ""]
        shown = list(task.target_files or [])
        shown += [e.file_path for e in self.impact_entries[:5]]
        for rel_path in shown:
            src = self._read_repo_file(self.repo_path, rel_path)
            if src:
                lines += [f"### `{rel_path}` ({task.repo})", "```", src[:self.MAX_FILE_CHARS], "```", ""]

        # RISK_MATRIX actual
        risk_matrix = self._read_risk_matrix()
        if risk_matrix:
            lines += ["## RISK_MATRIX actual del repo", "```", risk_matrix[:3_000], "```", ""]

        # Repos consumidores (cross-repo)
        consumers = self._get_consuming_repos()
        if consumers:
            lines += ["## Repos que consumen este servicio", ""]
            for repo_name, repo_path in consumers:
                lines.append(f"### {repo_name}")
                api_files = self._find_api_consumers(repo_path)
                for rel, src in api_files[:self.MAX_CONSUMERS]:
                    lines += [f"#### `{rel}` ({repo_name})", "```", src[:self.MAX_FILE_CHARS], "```", ""]
        lines.append("")

        # Instrucción final
        filename = f"alert-{task.type}-{task.task_id}.md"
        lines += [
            "---",
            "",
            f"Generá el archivo `{filename}` con exactamente este formato:",
            "",
            "```markdown",
            f"# ALERT — {task.type}-{task.task_id}: {task.title}",
            f"> Generado por Gemini | {{fecha}}",
            "",
            f"## Archivos afectados — {task.repo}",
            "| Archivo | Qué revisar / modificar |",
            "|---------|------------------------|",
            "| `ruta/archivo.py` | descripción concreta de qué cambiar |",
            "",
            "## Impacto cross-repo",
            "| Repo | Archivo | Qué revisar / modificar |",
            "|------|---------|------------------------|",
            "| `REPO-FE` | `ruta/service.ts` | descripción concreta |",
            "",
            "## Nivel de riesgo",
            "**NIVEL** — justificación en una línea",
            "```",
            "",
            "Si no hay impacto cross-repo, omití esa sección.",
            "Sé específico en el 'Qué revisar / modificar' — no uses frases genéricas.",
        ]

        return "\n".join(lines)

    # ─── Helpers de lectura ────────────────────────────────────────────────────

    def _read_repo_file(self, repo_path: str, rel_path: str) -> str | None:
        abs_path = os.path.join(repo_path, rel_path.replace("/", os.sep))
        if not os.path.exists(abs_path):
            return None
        try:
            with open(abs_path, encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    def _read_risk_matrix(self) -> str | None:
        path = os.path.join(
            self.cipher_dir, "clients", self.client_name,
            self.task.repo, "RISK_MATRIX.md",
        )
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    def _get_consuming_repos(self) -> list:
        """
        Devuelve [(repo_name, repo_path)] de repos que consumen el repo actual.
        Cruza depends_on y consumed_by del config.
        """
        current = self.task.repo
        result = []
        seen = set()

        for client_data in self.config.get("clients", {}).values():
            if not isinstance(client_data, dict):
                continue
            repos = client_data.get("repos", {})

            # Repos que listan al actual en depends_on
            for rname, rinfo in repos.items():
                if not isinstance(rinfo, dict):
                    continue
                if current in rinfo.get("depends_on", []):
                    rpath = rinfo.get("path", "")
                    if rpath and rname not in seen:
                        result.append((rname, rpath))
                        seen.add(rname)

            # consumed_by del repo actual
            current_info = repos.get(current, {})
            if isinstance(current_info, dict):
                for cb_name in current_info.get("consumed_by", []):
                    cb_info = repos.get(cb_name, {})
                    if isinstance(cb_info, dict):
                        cb_path = cb_info.get("path", "")
                        if cb_path and cb_name not in seen:
                            result.append((cb_name, cb_path))
                            seen.add(cb_name)

        return result

    def _find_api_consumers(self, repo_path: str) -> list:
        """
        Encuentra archivos en un repo externo que probablemente consumen la API.
        Busca por keywords de HTTP/fetch en archivos TS/JS/Python.
        """
        keywords = ["fetch(", "axios.", "/api/", "http", ".get(", ".post(",
                    "service", "Service", "client.", "Client"]
        results = []
        skip_dirs = {"node_modules", ".git", "__pycache__", "dist", ".next",
                     "build", ".turbo", "coverage"}

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in files:
                if not fname.endswith((".ts", ".tsx", ".js", ".jsx", ".py")):
                    continue
                abs_path = os.path.join(root, fname)
                try:
                    with open(abs_path, encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    if any(kw in content for kw in keywords):
                        rel = os.path.relpath(abs_path, repo_path).replace("\\", "/")
                        results.append((rel, content))
                except Exception:
                    continue
            if len(results) >= self.MAX_CONSUMERS:
                break

        return results

    # ─── Persistencia ─────────────────────────────────────────────────────────

    def _save(self, content: str) -> str:
        # 1. Copia activa en el repo del cliente (visible para el developer)
        repo_alert_path = os.path.join(self.repo_path, "CIPHER_ALERT.md")
        with open(repo_alert_path, "w", encoding="utf-8") as f:
            f.write(content)
        self._ensure_gitignore(self.repo_path, "CIPHER_ALERT.md")

        # 2. Copia de archivo en .cipher/alerts/ para trazabilidad
        alerts_dir = os.path.join(self.cipher_dir, ".cipher", "alerts", self.client_name)
        os.makedirs(alerts_dir, exist_ok=True)
        filename = f"alert-{self.task.type}-{self.task.task_id}.md"
        archive_path = os.path.join(alerts_dir, filename)
        with open(archive_path, "w", encoding="utf-8") as f:
            f.write(content)

        return repo_alert_path

    @staticmethod
    def _ensure_gitignore(repo_path: str, entry: str) -> None:
        """Agrega `entry` al .gitignore del repo si no está ya presente."""
        gitignore_path = os.path.join(repo_path, ".gitignore")
        try:
            if os.path.exists(gitignore_path):
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                if entry in lines:
                    return
                # Agrega con separador si el archivo no termina en newline
                with open(gitignore_path, "a", encoding="utf-8") as f:
                    if lines and lines[-1] != "":
                        f.write("\n")
                    f.write(f"{entry}\n")
            else:
                with open(gitignore_path, "w", encoding="utf-8") as f:
                    f.write(f"{entry}\n")
        except Exception:
            pass  # No bloquear el flujo si .gitignore no es accesible
