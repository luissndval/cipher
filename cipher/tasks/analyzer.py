"""
cipher tasks — TaskAnalyzer (F4-3)
Analiza una task para determinar tipo, archivos candidatos y generar TaskIntent.

Completamente determinístico: usa el índice y grafo, sin LLM.
"""

import re
from datetime import datetime, timezone

from cipher.tasks.schema import Task, TaskIntent, TaskType
from cipher.index.schema import RepoIndex
from cipher.graph.schema import DependencyGraph
from cipher.pack.scorer import score_files
from cipher.pack.builder import PackBuilder


# Palabras clave por tipo de tarea
_TYPE_PATTERNS = {
    TaskType.HOTFIX: re.compile(
        r"\b(hotfix|critical|urgente|urgent|p0|sev0|production|prod.?bug)\b", re.I
    ),
    TaskType.BUG: re.compile(
        r"\b(bug|fix|error|crash|falla|broken|roto|regresion|regression|exception|traceback)\b", re.I
    ),
    TaskType.FEATURE: re.compile(
        r"\b(feature|add|new|implement|create|agregar|nuevo|nueva|implementar|crear|soporte|support)\b", re.I
    ),
}

# Palabras clave para detectar restricciones arquitectónicas
_CONSTRAINT_PATTERNS = {
    "no modificar tests": re.compile(r"\b(no.?test|sin.?test|without.?test)\b", re.I),
    "solo backend": re.compile(r"\b(backend.?only|solo.?back|only.?server)\b", re.I),
    "solo frontend": re.compile(r"\b(frontend.?only|solo.?front|only.?client)\b", re.I),
    "no breaking changes": re.compile(r"\b(no.?breaking|backward.?compat|backwards.?compat)\b", re.I),
}

TOP_MODIFY_FILES = 5   # archivos con mayor score → candidatos a modificar
TOP_READ_FILES   = 10  # siguientes archivos → solo lectura / referencia


class TaskAnalyzer:
    def __init__(
        self,
        repo_index: RepoIndex,
        graph: DependencyGraph,
    ):
        self.repo_index = repo_index
        self.graph = graph

    def detect_type(self, title: str, description: str) -> str:
        """Detecta el tipo de tarea a partir del texto."""
        text = f"{title} {description}"
        for task_type in (TaskType.HOTFIX, TaskType.BUG, TaskType.FEATURE):
            if _TYPE_PATTERNS[task_type].search(text):
                return task_type.value
        return TaskType.TASK.value

    def detect_constraints(self, title: str, description: str) -> list:
        """Detecta restricciones arquitectónicas del texto."""
        text = f"{title} {description}"
        return [
            label
            for label, pattern in _CONSTRAINT_PATTERNS.items()
            if pattern.search(text)
        ]

    def find_candidate_files(self, title: str, description: str) -> tuple[list, list]:
        """
        Retorna (files_to_modify, files_to_read).
        Usa el scorer de Fase 3 para encontrar candidatos.
        """
        query = f"{title} {description}"
        scored = score_files(self.repo_index.files, query, self.graph)

        # Filtrar score > 0
        relevant = [(s, f) for s, f in scored if s > 0]

        modify_files = [f.path for _, f in relevant[:TOP_MODIFY_FILES]]

        # Expandir dependencias de los targets para files_to_read
        modify_set = set(modify_files)
        read_files = []
        for path in modify_files:
            for dep in self.graph.dependencies_of(path):
                if dep not in modify_set and dep not in read_files:
                    read_files.append(dep)
                if len(read_files) >= TOP_READ_FILES:
                    break

        # Rellenar read_files con siguientes scored si hay presupuesto
        for _, f in relevant[TOP_MODIFY_FILES:TOP_MODIFY_FILES + TOP_READ_FILES]:
            if f.path not in modify_set and f.path not in read_files:
                read_files.append(f.path)
            if len(read_files) >= TOP_READ_FILES:
                break

        return modify_files, read_files

    def build_intent(
        self,
        task: Task,
        context_pack_path: str = "",
        rules_applied: list | None = None,
    ) -> TaskIntent:
        """Genera el TaskIntent completo para una tarea."""
        modify_files, read_files = self.find_candidate_files(task.title, task.description)
        constraints = self.detect_constraints(task.title, task.description)

        return TaskIntent(
            task_id=task.task_id,
            task_type=task.type,
            title=task.title,
            description=task.description,
            repo=task.repo,
            files_to_modify=modify_files,
            files_to_read=read_files,
            rules_applied=rules_applied or [],
            constraints=constraints,
            context_pack_path=context_pack_path,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
