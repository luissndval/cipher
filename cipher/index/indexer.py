"""
cipher index — RepoIndexer
Recorre un repositorio, despacha a los parsers por lenguaje
y construye un RepoIndex determinístico.
No depende de cipher_dir — el caller decide dónde guardar el índice.
"""

import os
import json
import time
from datetime import datetime, timezone

from cipher import VERSION as BRAIN_VERSION
from cipher.index.schema import RepoIndex, IndexStats
from cipher.index.parsers.registry import get_parser

IGNORE_DIRS = {
    "node_modules", "__pycache__", "venv", ".venv", "dist", "build",
    ".git", ".idea", ".vscode", "coverage", ".next", ".nuxt", "out",
    "uploads", "migrations", "alembic",
}


class RepoIndexer:
    def __init__(self, repo_path: str, repo_name: str = None):
        self.repo_path = os.path.abspath(repo_path)
        self.repo_name = repo_name or os.path.basename(self.repo_path)

    def index(self, verbose: bool = False) -> RepoIndex:
        """
        Recorre el repo e indexa todos los archivos con parser disponible.
        Los errores de parse se registran en FileIndex.parse_error, no interrumpen.
        """
        start = time.time()
        file_indices = []
        lang_counts: dict[str, int] = {}

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = sorted(
                d for d in dirs
                if not d.startswith(".") and d not in IGNORE_DIRS
            )
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                parser = get_parser(ext)
                if parser is None:
                    continue

                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, self.repo_path).replace("\\", "/")

                fi = parser.parse(abs_path, rel_path)
                file_indices.append(fi)
                lang_counts[fi.language] = lang_counts.get(fi.language, 0) + 1

                if verbose and fi.parse_error:
                    print(f"    [WARN] {rel_path}: {fi.parse_error}")

        stats = IndexStats(
            total_files=len(file_indices),
            indexed_files=sum(1 for f in file_indices if f.parse_error is None),
            failed_files=sum(1 for f in file_indices if f.parse_error is not None),
            total_symbols=sum(len(f.symbols) for f in file_indices),
            total_imports=sum(len(f.imports) for f in file_indices),
            languages=lang_counts,
            duration_seconds=round(time.time() - start, 3),
            indexed_at=datetime.now(timezone.utc).isoformat(),
        )

        return RepoIndex(
            repo_name=self.repo_name,
            repo_path=self.repo_path,
            files=file_indices,
            stats=stats,
        )

    def save(self, repo_index: RepoIndex, output_dir: str) -> str:
        """Guarda el índice en output_dir/index.json. Crea el directorio si no existe."""
        os.makedirs(output_dir, exist_ok=True)
        index_path = os.path.join(output_dir, "index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(repo_index.to_dict(), f, indent=2, ensure_ascii=False)
        return index_path

    @staticmethod
    def load(index_path: str) -> RepoIndex:
        """Carga un RepoIndex desde un index.json en disco."""
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
        return RepoIndex.from_dict(data)
