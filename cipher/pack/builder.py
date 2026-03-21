"""
cipher pack — PackBuilder (F3-2 a F3-4)
Construye un ContextPack a partir de una descripción de tarea.

Pipeline:
  1. Puntúa todos los archivos del índice (scorer)
  2. Selecciona top candidatos como "target"
  3. Expande dependencias directas via grafo → "dependency"
  4. Lee contenido de disco y aplica budget manager
  5. Adjunta rules + architecture snippet
  6. Serializa a context_pack.md + context_manifest.json
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from cipher.index.schema import RepoIndex, FileIndex
from cipher.graph.schema import DependencyGraph
from cipher.pack.schema import ContextPack, PackEntry, PackManifest
from cipher.pack.scorer import score_files
from cipher.pack.budget import TokenBudget, estimate_tokens

BRAIN_VERSION = "0.3.0"
MAX_TARGET_FILES  = 10
MAX_DEPENDENCY_FILES = 20


class PackBuilder:
    def __init__(
        self,
        repo_index: RepoIndex,
        graph: DependencyGraph,
        repo_path: str,
        cipher_dir: str | None = None,
        client_name: str | None = None,
    ):
        self.repo_index = repo_index
        self.graph = graph
        self.repo_path = repo_path
        self.cipher_dir = cipher_dir
        self.client_name = client_name
        self._files_by_path: dict[str, FileIndex] = {
            f.path: f for f in repo_index.files
        }

    def build(
        self,
        task_description: str,
        provider: str = "claude",
        task_id: str | None = None,
    ) -> ContextPack:
        if not task_id:
            task_id = str(uuid.uuid4())[:8]

        budget = TokenBudget(provider)

        # 1. Puntuar y seleccionar targets
        scored = score_files(self.repo_index.files, task_description, self.graph)
        # Solo considerar archivos con score > 0
        candidates = [(s, f) for s, f in scored if s > 0]
        target_files = candidates[:MAX_TARGET_FILES]

        # 2. Expandir dependencias via grafo
        target_paths = {f.path for _, f in target_files}
        dep_paths: set[str] = set()
        for _, file_index in target_files:
            for dep_path in self.graph.dependencies_of(file_index.path):
                if dep_path not in target_paths:
                    dep_paths.add(dep_path)

        # Ordenar dependencias por inbound degree (más usadas primero)
        dep_files_scored = []
        for path in dep_paths:
            fi = self._files_by_path.get(path)
            if fi:
                inbound = len(self.graph.dependents_of(path))
                dep_files_scored.append((inbound, fi))
        dep_files_scored.sort(key=lambda x: x[0], reverse=True)
        dep_files = [(0.0, fi) for _, fi in dep_files_scored[:MAX_DEPENDENCY_FILES]]

        # 3. Leer contenido y aplicar budget
        entries: list[PackEntry] = []
        files_budget = budget.files_budget()
        per_file_budget = files_budget // max(1, len(target_files) + len(dep_files))

        for score, file_index in target_files:
            entry = self._make_entry(file_index, "target", score, per_file_budget)
            if entry:
                entries.append(entry)

        for score, file_index in dep_files:
            entry = self._make_entry(file_index, "dependency", score, per_file_budget)
            if entry:
                entries.append(entry)

        # 4. Rules + architecture
        rules_content = self._load_context_file("RULES.md", budget.rules_budget())
        arch_snippet   = self._load_context_file("ARCHITECTURE.md", budget.arch_budget())

        # 5. Calcular hash del pack
        pack_text = self._render_markdown(task_description, entries, rules_content, arch_snippet)
        pack_hash = hashlib.sha256(pack_text.encode("utf-8")).hexdigest()

        manifest = PackManifest(
            task_id=task_id,
            task_description=task_description,
            repo_name=self.repo_index.repo_name,
            repo_path=self.repo_path,
            built_at=datetime.now(timezone.utc).isoformat(),
            brain_version=BRAIN_VERSION,
            provider=provider,
            token_budget=budget.total,
            tokens_used=sum(e.tokens for e in entries),
            files_included=[e.to_dict() for e in entries],
            context_pack_hash=pack_hash,
        )

        return ContextPack(
            manifest=manifest,
            entries=entries,
            rules_content=rules_content,
            arch_snippet=arch_snippet,
        )

    # ─── Persistencia ─────────────────────────────────────────────────────────

    @staticmethod
    def save(pack: ContextPack, output_dir: str) -> tuple[str, str]:
        """
        Guarda context_pack.md y context_manifest.json en output_dir.
        Retorna (md_path, manifest_path).
        """
        os.makedirs(output_dir, exist_ok=True)

        task_id = pack.manifest.task_id
        desc_slug = _slugify(pack.manifest.task_description)[:40]
        folder_name = f"{task_id}_{desc_slug}" if desc_slug else task_id
        pack_dir = os.path.join(output_dir, folder_name)
        os.makedirs(pack_dir, exist_ok=True)

        md_content = _render_pack_md(pack)
        md_path = os.path.join(pack_dir, "context_pack.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        manifest_path = os.path.join(pack_dir, "context_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(pack.manifest.to_dict(), f, indent=2, ensure_ascii=False)

        return md_path, manifest_path

    @staticmethod
    def load_manifest(manifest_path: str) -> PackManifest:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return PackManifest.from_dict(json.load(f))

    # ─── Helpers privados ─────────────────────────────────────────────────────

    def _make_entry(
        self, file_index: FileIndex, role: str, score: float, max_tokens: int
    ) -> PackEntry | None:
        content = self._read_file(file_index.path)
        if content is None:
            return None
        trimmed, used = _trim(content, max_tokens)
        return PackEntry(
            path=file_index.path,
            language=file_index.language,
            role=role,
            score=score,
            tokens=used,
            content=trimmed,
        )

    def _read_file(self, rel_path: str) -> str | None:
        full = os.path.join(self.repo_path, rel_path.replace("/", os.sep))
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                with open(full, "r", encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        return None

    def _load_context_file(self, filename: str, max_tokens: int) -> str:
        """Intenta cargar un archivo de contexto del cliente cipher."""
        if not self.cipher_dir or not self.client_name:
            return ""
        repo_name = self.repo_index.repo_name
        path = os.path.join(
            self.cipher_dir, "clients", self.client_name, repo_name, filename
        )
        if not os.path.exists(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            trimmed, _ = _trim(content, max_tokens)
            return trimmed
        except Exception:
            return ""

    def _render_markdown(
        self,
        task_description: str,
        entries: list[PackEntry],
        rules: str,
        arch: str,
    ) -> str:
        return _render_pack_md_parts(task_description, entries, rules, arch,
                                     self.repo_index.repo_name)


# ─── Renderizado ──────────────────────────────────────────────────────────────

def _render_pack_md(pack: ContextPack) -> str:
    return _render_pack_md_parts(
        pack.manifest.task_description,
        pack.entries,
        pack.rules_content,
        pack.arch_snippet,
        pack.manifest.repo_name,
        pack.manifest,
    )


def _render_pack_md_parts(
    task_description: str,
    entries: list[PackEntry],
    rules: str,
    arch: str,
    repo_name: str,
    manifest: PackManifest | None = None,
) -> str:
    lines = []
    lines.append(f"# Context Pack — {repo_name}")
    if manifest:
        lines.append(f"\n**Task:** {task_description}")
        lines.append(f"**ID:** `{manifest.task_id}`  |  **Built:** {manifest.built_at}")
        lines.append(f"**Budget:** {manifest.tokens_used:,} / {manifest.token_budget:,} tokens  "
                     f"({100 * manifest.tokens_used // manifest.token_budget}% usado)")
    else:
        lines.append(f"\n**Task:** {task_description}")

    # Índice de archivos
    targets = [e for e in entries if e.role == "target"]
    deps    = [e for e in entries if e.role == "dependency"]

    if targets:
        lines.append("\n## Archivos objetivo")
        for e in targets:
            lines.append(f"- `{e.path}` ({e.language}, score={e.score:.1f}, ~{e.tokens:,}t)")

    if deps:
        lines.append("\n## Dependencias incluidas")
        for e in deps:
            lines.append(f"- `{e.path}` ({e.language}, ~{e.tokens:,}t)")

    # Rules
    if rules:
        lines.append("\n---\n## Reglas de negocio / arquitectura")
        lines.append(rules)

    # Architecture snippet
    if arch:
        lines.append("\n---\n## Arquitectura")
        lines.append(arch)

    # Contenido de archivos
    lines.append("\n---\n## Código fuente")
    for e in entries:
        lang = e.language or ""
        lines.append(f"\n### `{e.path}` ({e.role})")
        lines.append(f"```{lang}")
        lines.append(e.content)
        lines.append("```")

    return "\n".join(lines) + "\n"


def _trim(content: str, max_tokens: int) -> tuple[str, int]:
    max_chars = max_tokens * 4
    if len(content) <= max_chars:
        return content, estimate_tokens(content)
    trimmed = content[:max_chars]
    last_nl = trimmed.rfind("\n")
    if last_nl > max_chars * 0.8:
        trimmed = trimmed[:last_nl]
    trimmed += "\n\n... [truncado por budget] ..."
    return trimmed, estimate_tokens(trimmed)


def _slugify(text: str) -> str:
    import re
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return slug
