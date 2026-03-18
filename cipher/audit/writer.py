"""
cipher audit — AuditWriter (F5-2, F5-4)
Escribe manifests y entradas al audit log.

  manifest   → .cipher/sessions/<client>/<repo>/<task_id>/CONTEXT_MANIFEST.json
  audit log  → .cipher/audit/audit_log.jsonl  (append-only)
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from cipher.audit.schema import ContextManifest, AuditEntry, BRAIN_VERSION
from cipher.pack.schema import PackManifest


class AuditWriter:
    def __init__(self, cipher_dir: str):
        self.cipher_dir = cipher_dir
        self._audit_dir = os.path.join(cipher_dir, ".cipher", "audit")
        self._log_path  = os.path.join(self._audit_dir, "audit_log.jsonl")

    # ─── Manifest ─────────────────────────────────────────────────────────────

    def build_manifest(
        self,
        pack_manifest: PackManifest,
        event: str = "task_run",
        session_id: str = "",
        task_id: str = "",
    ) -> ContextManifest:
        """
        Construye un ContextManifest a partir del PackManifest de Fase 3.
        task_id: si se pasa vacío, usa el del pack.
        """
        tid = task_id or pack_manifest.task_id
        files_used = pack_manifest.files_included  # ya tiene {path, role, tokens, language}

        deps = [
            f["path"]
            for f in files_used
            if f.get("role") == "dependency"
        ]

        manifest_id = str(uuid.uuid4())
        manifest = ContextManifest(
            manifest_id=manifest_id,
            task_id=tid,
            session_id=session_id,
            event=event,
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=pack_manifest.provider,
            brain_version=BRAIN_VERSION,
            repo=pack_manifest.repo_name,
            client="",  # se rellena después si se conoce
            files_used=files_used,
            dependencies_included=deps,
            rules_applied=[],  # se puede enriquecer post-construcción
            token_budget=pack_manifest.token_budget,
            tokens_used=pack_manifest.tokens_used,
            context_pack_hash=pack_manifest.context_pack_hash,
            pr_url="",
            result="pending",
            manifest_path="",  # se rellena al guardar
        )
        return manifest

    def save_manifest(
        self,
        manifest: ContextManifest,
        client: str,
        repo: str,
        task_id: str,
    ) -> str:
        """
        Guarda CONTEXT_MANIFEST.json en
        .cipher/sessions/<client>/<repo>/<task_id>/CONTEXT_MANIFEST.json
        Retorna el path del archivo.
        """
        session_dir = os.path.join(
            self.cipher_dir, ".cipher", "sessions",
            client or "_", repo or "_", task_id,
        )
        os.makedirs(session_dir, exist_ok=True)
        path = os.path.join(session_dir, "CONTEXT_MANIFEST.json")
        manifest.client = client
        manifest.manifest_path = path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
        return path

    def update_manifest(self, manifest: ContextManifest, **kwargs) -> ContextManifest:
        """
        Actualiza campos del manifest en disco (ej: pr_url, result).
        """
        for k, v in kwargs.items():
            if hasattr(manifest, k):
                setattr(manifest, k, v)
        if manifest.manifest_path and os.path.exists(manifest.manifest_path):
            with open(manifest.manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
        return manifest

    # ─── Audit log ────────────────────────────────────────────────────────────

    def append_entry(self, manifest: ContextManifest):
        """Agrega una entrada al audit_log.jsonl (append-only)."""
        os.makedirs(self._audit_dir, exist_ok=True)
        entry = AuditEntry.from_manifest(manifest)
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        return entry

    def update_entry(self, manifest_id: str, **kwargs):
        """
        Actualiza campos de una entrada existente en el jsonl.
        Reescribe el archivo completo (el log es pequeño en práctica).
        """
        if not os.path.exists(self._log_path):
            return
        lines = []
        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("entry_id") == manifest_id:
                        entry.update(kwargs)
                    lines.append(entry)
                except json.JSONDecodeError:
                    continue
        with open(self._log_path, "w", encoding="utf-8") as f:
            for entry in lines:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @property
    def log_path(self) -> str:
        return self._log_path
