"""
cipher pack — Schema (F3-1)
Estructuras de datos del Context Pack.

Terminología:
  target      : archivo directamente relevante para la tarea (alta relevancia léxica)
  dependency  : importado por un target (expansión via grafo)
  context     : archivos de contexto adicional (rules, architecture)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PackEntry:
    """Un archivo incluido en el context pack."""
    path: str
    language: str
    role: str          # "target" | "dependency" | "context"
    score: float       # relevancia calculada (mayor = más importante)
    tokens: int        # tokens estimados del contenido incluido
    content: str       # contenido real del archivo (puede estar truncado)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "language": self.language,
            "role": self.role,
            "score": self.score,
            "tokens": self.tokens,
            # content excluido del dict por tamaño
        }


@dataclass
class PackManifest:
    """Metadata del context pack generado."""
    task_id: str
    task_description: str
    repo_name: str
    repo_path: str
    built_at: str           # ISO 8601 UTC
    brain_version: str
    provider: str           # "claude" | "gemini" | "unknown"
    token_budget: int
    tokens_used: int
    files_included: list    # list[dict] con {path, role, score, tokens}
    context_pack_hash: str  # SHA-256 del contenido completo del pack

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "repo_name": self.repo_name,
            "repo_path": self.repo_path,
            "built_at": self.built_at,
            "brain_version": self.brain_version,
            "provider": self.provider,
            "token_budget": self.token_budget,
            "tokens_used": self.tokens_used,
            "files_included": self.files_included,
            "context_pack_hash": self.context_pack_hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PackManifest":
        return cls(
            task_id=d["task_id"],
            task_description=d.get("task_description", ""),
            repo_name=d["repo_name"],
            repo_path=d["repo_path"],
            built_at=d.get("built_at", ""),
            brain_version=d.get("brain_version", ""),
            provider=d.get("provider", "unknown"),
            token_budget=d.get("token_budget", 0),
            tokens_used=d.get("tokens_used", 0),
            files_included=d.get("files_included", []),
            context_pack_hash=d.get("context_pack_hash", ""),
        )


@dataclass
class ContextPack:
    """Context pack completo: archivos + reglas + arquitectura + manifest."""
    manifest: PackManifest
    entries: list         # list[PackEntry], ordenado por prioridad
    rules_content: str    # contenido del archivo de reglas (puede ser "")
    arch_snippet: str     # fragmento relevante de ARCHITECTURE.md (puede ser "")
