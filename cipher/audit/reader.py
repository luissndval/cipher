"""
cipher audit — AuditReader (F5-5)
Lee y filtra el audit log y los manifests individuales.
"""

import json
import os
from datetime import datetime, timezone

from cipher.audit.schema import AuditEntry, ContextManifest
from cipher.core.paths import to_abs


class AuditReader:
    def __init__(self, cipher_dir: str):
        self.cipher_dir = cipher_dir
        self._log_path = os.path.join(cipher_dir, ".cipher", "audit", "audit_log.jsonl")

    def entries(
        self,
        task_id: str | None = None,
        repo: str | None = None,
        client: str | None = None,
        event: str | None = None,
        result: str | None = None,
        since: str | None = None,   # ISO date prefix, e.g. "2024-01"
        limit: int = 100,
    ) -> list:
        """
        Retorna list[AuditEntry] filtrado por los criterios dados.
        Ordenado por timestamp desc (más reciente primero).
        """
        if not os.path.exists(self._log_path):
            return []

        results = []
        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if task_id  and d.get("task_id")  != task_id:
                    continue
                if repo     and d.get("repo")     != repo:
                    continue
                if client   and d.get("client")   != client:
                    continue
                if event    and d.get("event")    != event:
                    continue
                if result   and d.get("result")   != result:
                    continue
                if since    and not d.get("timestamp", "").startswith(since):
                    continue

                results.append(AuditEntry.from_dict(d))

        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def load_manifest(self, manifest_path: str) -> ContextManifest | None:
        """Carga el ContextManifest completo desde disco."""
        # Resolver relativo → absoluto (retrocompatible con JSONs viejos que ya son absolutos)
        abs_path = to_abs(manifest_path, self.cipher_dir)
        if not abs_path or not os.path.exists(abs_path):
            return None
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Restaurar manifest_path como absoluto en memoria
            data["manifest_path"] = abs_path
            return ContextManifest.from_dict(data)
        except Exception:
            return None

    def find_manifest(self, task_id: str) -> ContextManifest | None:
        """Busca el manifest de una task por su task_id."""
        entries = self.entries(task_id=task_id, limit=1)
        if not entries:
            return None
        return self.load_manifest(entries[0].manifest_path)

    def stats(self) -> dict:
        """Estadísticas rápidas del audit log."""
        all_entries = self.entries(limit=10_000)
        if not all_entries:
            return {"total": 0}

        total_tokens = sum(e.tokens_used for e in all_entries)
        by_result = {}
        by_repo = {}
        for e in all_entries:
            by_result[e.result] = by_result.get(e.result, 0) + 1
            by_repo[e.repo] = by_repo.get(e.repo, 0) + 1

        return {
            "total": len(all_entries),
            "total_tokens_used": total_tokens,
            "by_result": by_result,
            "by_repo": by_repo,
            "latest": all_entries[0].timestamp if all_entries else "",
        }
