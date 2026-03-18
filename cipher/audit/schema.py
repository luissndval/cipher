"""
cipher audit — Schema (F5-1)
Estructuras de datos del sistema de manifest y auditoría.

Terminología:
  ContextManifest : registro completo de qué evidencia usó la IA en una sesión/task
  AuditEntry      : entrada slim en el audit log (jsonl), apunta al manifest completo
"""

from dataclasses import dataclass, field
from typing import Optional

BRAIN_VERSION = "0.5.0"


@dataclass
class ContextManifest:
    """
    Registro completo de la evidencia que el agente IA recibió.
    Se guarda en .cipher/sessions/<client>/<repo>/<task_id>/CONTEXT_MANIFEST.json
    """
    manifest_id: str          # UUID
    task_id: str              # de la task asociada, o "" para sesiones directas
    session_id: str           # de SessionStore, o ""
    event: str                # "session_start" | "task_run"
    timestamp: str            # ISO 8601 UTC
    model: str                # "claude" | "gemini" | proveedor
    brain_version: str
    repo: str
    client: str

    # Contexto utilizado
    files_used: list          # list[dict] con {path, role, tokens, language}
    dependencies_included: list  # list[str] — paths expandidos desde el grafo
    rules_applied: list       # list[str] — reglas detectadas/incluidas
    token_budget: int
    tokens_used: int
    context_pack_hash: str    # SHA-256 del pack enviado

    # Post-sesión (se rellena después)
    pr_url: str               # URL del PR creado (vacío hasta que se cree)
    result: str               # "pending" | "done" | "failed"
    manifest_path: str        # path de este archivo en disco

    def to_dict(self) -> dict:
        return {
            "manifest_id": self.manifest_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "event": self.event,
            "timestamp": self.timestamp,
            "model": self.model,
            "brain_version": self.brain_version,
            "repo": self.repo,
            "client": self.client,
            "files_used": self.files_used,
            "dependencies_included": self.dependencies_included,
            "rules_applied": self.rules_applied,
            "token_budget": self.token_budget,
            "tokens_used": self.tokens_used,
            "context_pack_hash": self.context_pack_hash,
            "pr_url": self.pr_url,
            "result": self.result,
            "manifest_path": self.manifest_path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ContextManifest":
        return cls(
            manifest_id=d.get("manifest_id", ""),
            task_id=d.get("task_id", ""),
            session_id=d.get("session_id", ""),
            event=d.get("event", "session_start"),
            timestamp=d.get("timestamp", ""),
            model=d.get("model", ""),
            brain_version=d.get("brain_version", ""),
            repo=d.get("repo", ""),
            client=d.get("client", ""),
            files_used=d.get("files_used", []),
            dependencies_included=d.get("dependencies_included", []),
            rules_applied=d.get("rules_applied", []),
            token_budget=d.get("token_budget", 0),
            tokens_used=d.get("tokens_used", 0),
            context_pack_hash=d.get("context_pack_hash", ""),
            pr_url=d.get("pr_url", ""),
            result=d.get("result", "pending"),
            manifest_path=d.get("manifest_path", ""),
        )

    @property
    def files_count(self) -> int:
        return len(self.files_used)

    @property
    def budget_pct(self) -> int:
        if not self.token_budget:
            return 0
        return min(100, 100 * self.tokens_used // self.token_budget)


@dataclass
class AuditEntry:
    """
    Entrada slim en audit_log.jsonl.
    Apunta al ContextManifest completo para consultas de detalle.
    """
    entry_id: str
    timestamp: str
    event: str
    task_id: str
    session_id: str
    repo: str
    client: str
    model: str
    tokens_used: int
    files_count: int
    context_pack_hash: str
    pr_url: str
    result: str
    manifest_path: str    # path al CONTEXT_MANIFEST.json

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "event": self.event,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "repo": self.repo,
            "client": self.client,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "files_count": self.files_count,
            "context_pack_hash": self.context_pack_hash,
            "pr_url": self.pr_url,
            "result": self.result,
            "manifest_path": self.manifest_path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AuditEntry":
        return cls(
            entry_id=d.get("entry_id", ""),
            timestamp=d.get("timestamp", ""),
            event=d.get("event", ""),
            task_id=d.get("task_id", ""),
            session_id=d.get("session_id", ""),
            repo=d.get("repo", ""),
            client=d.get("client", ""),
            model=d.get("model", ""),
            tokens_used=d.get("tokens_used", 0),
            files_count=d.get("files_count", 0),
            context_pack_hash=d.get("context_pack_hash", ""),
            pr_url=d.get("pr_url", ""),
            result=d.get("result", "pending"),
            manifest_path=d.get("manifest_path", ""),
        )

    @classmethod
    def from_manifest(cls, manifest: ContextManifest) -> "AuditEntry":
        return cls(
            entry_id=manifest.manifest_id,
            timestamp=manifest.timestamp,
            event=manifest.event,
            task_id=manifest.task_id,
            session_id=manifest.session_id,
            repo=manifest.repo,
            client=manifest.client,
            model=manifest.model,
            tokens_used=manifest.tokens_used,
            files_count=manifest.files_count,
            context_pack_hash=manifest.context_pack_hash,
            pr_url=manifest.pr_url,
            result=manifest.result,
            manifest_path=manifest.manifest_path,
        )
