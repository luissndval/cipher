"""
cipher memory — SessionStore
Gestiona el ciclo de vida de sesiones: session_id, metadata y manifests.
Cada sesión genera un CONTEXT_MANIFEST.json auditable.
"""

import os
import json
import hashlib
import uuid
from datetime import datetime, timezone

from cipher import VERSION as BRAIN_VERSION


class SessionStore:
    def __init__(self, cipher_dir: str):
        self.cipher_dir = cipher_dir

    # ─── Ciclo de vida ────────────────────────────────────────────────────────

    def new_session(self, client: str, project: str, agent: str, repo_path: str) -> dict:
        """Crea un nuevo registro de sesión con ID único."""
        return {
            "session_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client": client,
            "project": project,
            "agent": agent,
            "repo_path": repo_path,
            "brain_version": BRAIN_VERSION,
            "context_file": None,
            "context_hash": None,
            "task_file": None,
            "model": None,
            "status": "started",
        }

    def attach_context(self, session: dict, context_path: str) -> dict:
        """Agrega referencia al archivo de contexto y su hash SHA-256."""
        session["context_file"] = context_path
        if os.path.exists(context_path):
            with open(context_path, "rb") as f:
                session["context_hash"] = hashlib.sha256(f.read()).hexdigest()[:16]
        return session

    def attach_task(self, session: dict, task_path: str) -> dict:
        session["task_file"] = task_path
        return session

    def attach_model(self, session: dict, model: str) -> dict:
        session["model"] = model
        return session

    def close_session(self, session: dict, status: str = "completed") -> dict:
        session["status"] = status
        session["closed_at"] = datetime.now(timezone.utc).isoformat()
        return session

    # ─── Persistencia ─────────────────────────────────────────────────────────

    def save_manifest(self, session: dict, client: str, project: str) -> str:
        """
        Guarda el manifest en:
        .cipher/sessions/<client>/<project>/<session_id>/session_manifest.json
        """
        session_dir = os.path.join(
            self.cipher_dir, ".cipher", "sessions",
            client, project, session["session_id"]
        )
        os.makedirs(session_dir, exist_ok=True)
        manifest_path = os.path.join(session_dir, "session_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        return manifest_path

    def load_latest_manifest(self, client: str, project: str) -> dict | None:
        """Retorna el manifest más reciente para un proyecto."""
        base = os.path.join(self.cipher_dir, ".cipher", "sessions", client, project)
        if not os.path.exists(base):
            return None
        sessions = sorted(
            [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))],
            reverse=True,
        )
        for s in sessions:
            manifest = os.path.join(base, s, "session_manifest.json")
            if os.path.exists(manifest):
                with open(manifest) as f:
                    return json.load(f)
        return None

    def list_manifests(self, client: str = None, project: str = None) -> list:
        """Lista todos los manifests, con filtro opcional por cliente/proyecto."""
        results = []
        base = os.path.join(self.cipher_dir, ".cipher", "sessions")
        if not os.path.exists(base):
            return results

        clients = [client] if client else os.listdir(base)
        for c in clients:
            c_dir = os.path.join(base, c)
            if not os.path.isdir(c_dir):
                continue
            projects = [project] if project else os.listdir(c_dir)
            for p in projects:
                p_dir = os.path.join(c_dir, p)
                if not os.path.isdir(p_dir):
                    continue
                for s in os.listdir(p_dir):
                    manifest = os.path.join(p_dir, s, "session_manifest.json")
                    if os.path.exists(manifest):
                        with open(manifest) as f:
                            results.append(json.load(f))

        return sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
