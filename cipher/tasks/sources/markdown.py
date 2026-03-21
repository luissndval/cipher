"""
cipher tasks — MarkdownSource
Carga una task desde un archivo .md local.

Formato del archivo (todo opcional salvo existir):

  # Título de la tarea

  Descripción libre, puede ocupar varios párrafos.

  Link: https://linear.app/acme/issue/ENG-4040

El nombre del archivo codifica tipo y número:
  feature-4040-mi-tarea.md  → FEATURE, ticket 4040
  bug-123-fix-login.md      → BUG,     ticket 123
  hotfix-7-crash.md         → HOTFIX,  ticket 7
  task-99-refactor.md       → TASK,    ticket 99
  cualquier-cosa.md         → TASK,    número autogenerado

Si el archivo no tiene # Título, se usa el slug del nombre de archivo.
"""

import os
import re
from datetime import datetime, timezone

from cipher.tasks.sources.base import TicketSource, RawTicket

_TYPE_MAP = {
    "feature": "FEATURE",
    "feat":    "FEATURE",
    "bug":     "BUG",
    "fix":     "BUG",
    "hotfix":  "HOTFIX",
    "task":    "TASK",
    "chore":   "TASK",
    "refactor":"TASK",
}


class MarkdownSource(TicketSource):

    @property
    def name(self) -> str:
        return "markdown"

    def fetch(self, ref: str) -> RawTicket:
        """ref: ruta al archivo .md (absoluta o relativa al CWD)."""
        path = os.path.abspath(ref)
        if not os.path.exists(path):
            raise ValueError(f"Archivo no encontrado: {path}")

        with open(path, encoding="utf-8") as f:
            content = f.read()

        stem = os.path.splitext(os.path.basename(path))[0]  # "feature-4040-mi-tarea"
        work_type, number, title_from_file, branch = self._parse_filename(stem)

        # Extraer título del cuerpo (primer # H1)
        title_from_body = self._extract_h1(content)
        title = title_from_body or self._slug_to_title(stem)

        # Extraer link (línea "Link: <url>" o "**Link:** <url>")
        link = self._extract_link(content)

        # Descripción = todo el cuerpo sin el H1 ni la línea de link
        description = self._extract_description(content)

        # Rama: tipo-numero-slug-del-titulo
        title_slug = re.sub(r"[^a-zA-Z0-9\s]", "", title)
        title_slug = re.sub(r"\s+", "-", title_slug.strip()).lower()
        branch = f"{work_type.lower()}-{number}-{title_slug}"

        full_description = description
        if link:
            full_description = f"{description}\n\nLink: {link}".strip()

        return RawTicket(
            title=f"[{work_type}-{number}] {title}",
            description=full_description,
            source="markdown",
            source_ref=link,
            labels=[work_type.lower()],
            extra={
                "work_type": work_type,
                "number":    number,
                "branch":    branch,
                "md_path":   path,
            },
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _parse_filename(self, stem: str) -> tuple:
        """
        Extrae (work_type, number, title_slug, branch) del nombre del archivo.
        Soporta: feature-4040-mi-tarea  |  bug-123  |  fix-login-timeout
        """
        parts = stem.split("-")
        work_type = _TYPE_MAP.get(parts[0].lower(), "TASK")
        number = None
        slug_start = 1

        if len(parts) > 1 and parts[1].isdigit():
            number = parts[1]
            slug_start = 2

        if not number:
            number = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")

        title_slug = "-".join(parts[slug_start:]) if len(parts) > slug_start else stem
        branch = f"{work_type.lower()}-{number}-{title_slug}"
        return work_type, number, title_slug, branch

    def _extract_h1(self, content: str) -> str:
        """Retorna el texto del primer encabezado # del archivo."""
        for line in content.splitlines():
            m = re.match(r"^#\s+(.+)", line)
            if m:
                return m.group(1).strip()
        return ""

    def _extract_link(self, content: str) -> str:
        """Busca líneas del tipo 'Link: <url>' o '**Link:** <url>'."""
        for line in content.splitlines():
            m = re.match(r"^\*{0,2}[Ll]ink\*{0,2}:\s*(.+)", line.strip())
            if m:
                return m.group(1).strip()
        return ""

    def _extract_description(self, content: str) -> str:
        """Cuerpo limpio: sin el H1 ni la línea Link."""
        lines = []
        for line in content.splitlines():
            if re.match(r"^#\s+", line):
                continue
            if re.match(r"^\*{0,2}[Ll]ink\*{0,2}:\s*", line.strip()):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def _slug_to_title(self, stem: str) -> str:
        """feature-4040-fix-login → Fix Login (fallback si no hay H1)."""
        parts = stem.split("-")
        # Saltar tipo y número
        start = 1
        if len(parts) > 1 and parts[1].isdigit():
            start = 2
        return " ".join(p.capitalize() for p in parts[start:]) or stem
