"""
cipher audit — PR Comment Generator (F5-3)
Genera el markdown del comentario de PR con el CONTEXT_MANIFEST.

El comentario es:
  - Resumen de qué evidencia usó la IA
  - Tabla de archivos incluidos en el contexto
  - Reglas y restricciones aplicadas
  - Hash del pack para reproducibilidad

Este módulo solo genera el markdown — no hace llamadas HTTP.
El posteo al PR es responsabilidad del comando que invoque esto (Fase 6 + cipher audit).
"""

from cipher.audit.schema import ContextManifest


_ROLE_EMOJI = {
    "target":     "🎯",
    "dependency": "🔗",
    "context":    "📄",
}


def generate_pr_comment(manifest: ContextManifest, include_hash: bool = True) -> str:
    """
    Genera el markdown completo del comentario de PR.
    Retorna un string listo para postear.
    """
    lines = []
    lines.append("## 🤖 Context usado por la IA\n")
    lines.append(f"**Task:** `{manifest.task_id}`  |  "
                 f"**Modelo:** `{manifest.model}`  |  "
                 f"**Brain v{manifest.brain_version}**\n")

    # Tokens
    pct = manifest.budget_pct
    bar = _progress_bar(pct)
    lines.append(f"**Tokens:** {manifest.tokens_used:,} / {manifest.token_budget:,} "
                 f"({pct}%) {bar}\n")

    # Tabla de archivos
    if manifest.files_used:
        lines.append("### Archivos incluidos\n")
        lines.append("| Archivo | Rol | Tokens |")
        lines.append("|---------|-----|--------|")
        for f in manifest.files_used:
            role = f.get("role", "")
            emoji = _ROLE_EMOJI.get(role, "📄")
            path = f.get("path", "")
            tokens = f.get("tokens", 0)
            lines.append(f"| `{path}` | {emoji} {role} | ~{tokens:,} |")
        lines.append("")

    # Reglas aplicadas
    if manifest.rules_applied:
        lines.append("### Reglas aplicadas")
        for rule in manifest.rules_applied:
            lines.append(f"- {rule}")
        lines.append("")

    # Dependencias incluidas (resumen)
    if manifest.dependencies_included:
        lines.append(f"**Dependencias expandidas:** "
                     f"{len(manifest.dependencies_included)} archivo(s)\n")
        for dep in manifest.dependencies_included[:5]:
            lines.append(f"  - `{dep}`")
        if len(manifest.dependencies_included) > 5:
            lines.append(f"  - _... y {len(manifest.dependencies_included) - 5} más_")
        lines.append("")

    # Hash
    if include_hash and manifest.context_pack_hash:
        lines.append(
            f"<details><summary>Reproducibilidad</summary>\n\n"
            f"**Context pack hash:** `{manifest.context_pack_hash}`  \n"
            f"**Timestamp:** {manifest.timestamp}\n\n"
            f"</details>\n"
        )

    lines.append("---")
    lines.append("_Generado por [cipher](https://github.com/luissndval/lore) "
                 "— System Brain v" + manifest.brain_version + "_")

    return "\n".join(lines) + "\n"


def _progress_bar(pct: int, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)
