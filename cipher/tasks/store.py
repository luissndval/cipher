"""
cipher tasks — TaskStore
Persistencia de tasks en .cipher/tasks/<client>/<repo>/<task_id>.json
"""

import json
import os

from cipher.tasks.schema import Task, TaskIntent, TaskStatus
from cipher.core.paths import to_rel, to_abs


class TaskStore:
    def __init__(self, cipher_dir: str):
        self.cipher_dir = cipher_dir
        self._tasks_root = os.path.join(cipher_dir, ".cipher", "tasks")

    # ─── Tasks ────────────────────────────────────────────────────────────────

    def save_task(self, task: Task) -> str:
        """Guarda task en disco. Retorna el path del archivo."""
        task_dir = self._task_dir(task.client, task.repo, task.task_id)
        os.makedirs(task_dir, exist_ok=True)
        path = os.path.join(task_dir, "task.json")
        data = task.to_dict()
        # Guardar intent_path relativo al cipher_dir para portabilidad
        if data.get("intent_path"):
            data["intent_path"] = to_rel(data["intent_path"], self.cipher_dir)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def load_task(self, client: str, repo: str, task_id: str) -> Task | None:
        path = os.path.join(self._task_dir(client, repo, task_id), "task.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Resolver intent_path a absoluto
        if data.get("intent_path"):
            data["intent_path"] = to_abs(data["intent_path"], self.cipher_dir)
        return Task.from_dict(data)

    def update_status(self, task: Task, status: str) -> Task:
        task.status = status
        self.save_task(task)
        return task

    def list_tasks(
        self,
        client: str | None = None,
        repo: str | None = None,
        status: str | None = None,
    ) -> list:
        """Retorna list[Task] filtrado por cliente/repo/status."""
        results = []
        root = self._tasks_root
        if not os.path.exists(root):
            return []

        for c in os.listdir(root):
            if client and c != client:
                continue
            client_dir = os.path.join(root, c)
            if not os.path.isdir(client_dir):
                continue
            for r in os.listdir(client_dir):
                if repo and r != repo:
                    continue
                repo_dir = os.path.join(client_dir, r)
                if not os.path.isdir(repo_dir):
                    continue
                for tid in os.listdir(repo_dir):
                    task_file = os.path.join(repo_dir, tid, "task.json")
                    if not os.path.exists(task_file):
                        continue
                    try:
                        with open(task_file, encoding="utf-8") as f:
                            task = Task.from_dict(json.load(f))
                        if status and task.status != status:
                            continue
                        results.append(task)
                    except Exception:
                        continue

        return sorted(results, key=lambda t: t.created_at, reverse=True)

    # ─── Intents ──────────────────────────────────────────────────────────────

    def save_intent(self, intent: TaskIntent, client: str, repo: str) -> str:
        task_dir = self._task_dir(client, repo, intent.task_id)
        os.makedirs(task_dir, exist_ok=True)
        path = os.path.join(task_dir, "task_intent.json")
        data = intent.to_dict()
        # Guardar context_pack_path relativo al cipher_dir para portabilidad
        if data.get("context_pack_path"):
            data["context_pack_path"] = to_rel(data["context_pack_path"], self.cipher_dir)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def load_intent(self, client: str, repo: str, task_id: str) -> TaskIntent | None:
        path = os.path.join(self._task_dir(client, repo, task_id), "task_intent.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Resolver context_pack_path a absoluto
        if data.get("context_pack_path"):
            data["context_pack_path"] = to_abs(data["context_pack_path"], self.cipher_dir)
        return TaskIntent.from_dict(data)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _task_dir(self, client: str, repo: str, task_id: str) -> str:
        return os.path.join(self._tasks_root, client or "_", repo or "_", task_id)

    def task_dir_path(self, task: Task) -> str:
        return self._task_dir(task.client, task.repo, task.task_id)
