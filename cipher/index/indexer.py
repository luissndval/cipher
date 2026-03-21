"""
cipher index — RepoIndexer
Recorre un repositorio, despacha a los parsers por lenguaje
y construye un RepoIndex determinístico.
No depende de cipher_dir — el caller decide dónde guardar el índice.
"""

import hashlib
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

    @staticmethod
    def _compute_hash(abs_path: str) -> str:
        """Calcula el SHA-256 del contenido de un archivo."""
        h = hashlib.sha256()
        with open(abs_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def index(self, verbose: bool = False, existing_index: RepoIndex = None) -> RepoIndex:
        """
        Recorre el repo e indexa todos los archivos con parser disponible.
        Si se provee existing_index, reutiliza entradas cuyo hash SHA-256 no cambió.
        Los errores de parse se registran en FileIndex.parse_error, no interrumpen.
        """
        start = time.time()
        file_indices = []
        lang_counts: dict[str, int] = {}

        # Construir lookup de entradas previas por path → FileIndex (solo si tienen hash)
        cached: dict[str, object] = {}
        if existing_index:
            for fi in existing_index.files:
                if fi.content_hash:
                    cached[fi.path] = fi

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

                # Indexación incremental: comparar hash
                current_hash = self._compute_hash(abs_path)
                if rel_path in cached and cached[rel_path].content_hash == current_hash:
                    fi = cached[rel_path]
                else:
                    fi = parser.parse(abs_path, rel_path)
                    fi.content_hash = current_hash

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
