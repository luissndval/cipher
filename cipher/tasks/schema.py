"""
cipher tasks — Schema (F4-1)
Estructuras de datos del Task Engine.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class TaskType(str, Enum):
    FEATURE = "FEATURE"
    BUG     = "BUG"
    HOTFIX  = "HOTFIX"
    TASK    = "TASK"


class TaskStatus(str, Enum):
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE        = "DONE"
    FAILED      = "FAILED"


@dataclass
class Task:
    """Unidad de trabajo formalizada para el agente IA."""
    task_id: str
    type: str              # TaskType value
    title: str
    description: str
    repo: str              # repo_name
    client: str
    status: str            # TaskStatus value
    created_at: str        # ISO 8601
    source: str            # "manual" | "github" | "linear"
    source_ref: str        # URL o ID de origen (vacío si manual)
    target_files: list     # list[str] — archivos identificados como objetivo
    context_pack_id: str   # task_id del pack asociado (vacío hasta que se construya)
    intent_path: str       # path al task_intent.json (vacío hasta que se genere)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "repo": self.repo,
            "client": self.client,
            "status": self.status,
            "created_at": self.created_at,
            "source": self.source,
            "source_ref": self.source_ref,
            "target_files": self.target_files,
            "context_pack_id": self.context_pack_id,
            "intent_path": self.intent_path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        return cls(
            task_id=d["task_id"],
            type=d.get("type", TaskType.TASK),
            title=d.get("title", ""),
            description=d.get("description", ""),
            repo=d.get("repo", ""),
            client=d.get("client", ""),
            status=d.get("status", TaskStatus.PENDING),
            created_at=d.get("created_at", ""),
            source=d.get("source", "manual"),
            source_ref=d.get("source_ref", ""),
            target_files=d.get("target_files", []),
            context_pack_id=d.get("context_pack_id", ""),
            intent_path=d.get("intent_path", ""),
        )


@dataclass
class TaskIntent:
    """
    Intención estructurada generada por el TaskAnalyzer.
    Es el input formal que recibe el agente junto con el context pack.
    """
    task_id: str
    task_type: str
    title: str
    description: str
    repo: str
    files_to_modify: list     # list[str] — paths con alta probabilidad de cambio
    files_to_read: list       # list[str] — paths de referencia (dependencias)
    rules_applied: list       # list[str] — reglas de negocio relevantes detectadas
    constraints: list         # list[str] — restricciones arquitectónicas
    context_pack_path: str    # path al context_pack.md
    generated_at: str         # ISO 8601

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "title": self.title,
            "description": self.description,
            "repo": self.repo,
            "files_to_modify": self.files_to_modify,
            "files_to_read": self.files_to_read,
            "rules_applied": self.rules_applied,
            "constraints": self.constraints,
            "context_pack_path": self.context_pack_path,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskIntent":
        return cls(
            task_id=d["task_id"],
            task_type=d.get("task_type", TaskType.TASK),
            title=d.get("title", ""),
            description=d.get("description", ""),
            repo=d.get("repo", ""),
            files_to_modify=d.get("files_to_modify", []),
            files_to_read=d.get("files_to_read", []),
            rules_applied=d.get("rules_applied", []),
            constraints=d.get("constraints", []),
            context_pack_path=d.get("context_pack_path", ""),
            generated_at=d.get("generated_at", ""),
        )
