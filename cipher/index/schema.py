"""
cipher index — Schema
Estructuras de datos para el índice estructural de repos.
Todo es serializable a/desde JSON via to_dict() / from_dict().
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Import:
    """Representa un import/require en un archivo fuente."""
    module: str           # "os.path", "react", "./utils", "github.com/gin-gonic/gin"
    names: list           # ["join"] o [] para "import os" o "import 'side-effect'"
    alias: Optional[str]  # "np" para "import numpy as np"
    is_relative: bool     # True para "./utils", "../models", "from . import x"
    line: int             # 1-indexed

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "names": self.names,
            "alias": self.alias,
            "is_relative": self.is_relative,
            "line": self.line,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Import":
        return cls(
            module=d["module"],
            names=d.get("names", []),
            alias=d.get("alias"),
            is_relative=d.get("is_relative", False),
            line=d.get("line", 0),
        )


@dataclass
class Symbol:
    """Representa un símbolo definido en un archivo fuente."""
    name: str             # "MyClass", "my_function", "Handler"
    kind: str             # "class" | "function" | "method" | "interface" | "struct"
    line: int             # 1-indexed
    parent: Optional[str] # nombre de la clase contenedora (para methods)
    decorators: list      # ["staticmethod", "Injectable"] — Python y TS

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "line": self.line,
            "parent": self.parent,
            "decorators": self.decorators,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Symbol":
        return cls(
            name=d["name"],
            kind=d["kind"],
            line=d.get("line", 0),
            parent=d.get("parent"),
            decorators=d.get("decorators", []),
        )


@dataclass
class FileIndex:
    """Índice estructural de un archivo fuente."""
    path: str             # path relativo al repo root, siempre con forward slashes
    language: str         # "python" | "typescript" | "go"
    imports: list         # list[Import]
    symbols: list         # list[Symbol]
    parse_error: Optional[str]  # None si OK, mensaje de error si falló
    size_bytes: int
    lines: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "language": self.language,
            "imports": [i.to_dict() for i in self.imports],
            "symbols": [s.to_dict() for s in self.symbols],
            "parse_error": self.parse_error,
            "size_bytes": self.size_bytes,
            "lines": self.lines,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FileIndex":
        return cls(
            path=d["path"],
            language=d["language"],
            imports=[Import.from_dict(i) for i in d.get("imports", [])],
            symbols=[Symbol.from_dict(s) for s in d.get("symbols", [])],
            parse_error=d.get("parse_error"),
            size_bytes=d.get("size_bytes", 0),
            lines=d.get("lines", 0),
        )


@dataclass
class IndexStats:
    """Estadísticas de una ejecución de indexación."""
    total_files: int
    indexed_files: int
    failed_files: int
    total_symbols: int
    total_imports: int
    languages: dict       # {"python": 12, "typescript": 8}
    duration_seconds: float
    indexed_at: str       # ISO 8601 UTC

    def to_dict(self) -> dict:
        return {
            "total_files": self.total_files,
            "indexed_files": self.indexed_files,
            "failed_files": self.failed_files,
            "total_symbols": self.total_symbols,
            "total_imports": self.total_imports,
            "languages": self.languages,
            "duration_seconds": self.duration_seconds,
            "indexed_at": self.indexed_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "IndexStats":
        return cls(
            total_files=d.get("total_files", 0),
            indexed_files=d.get("indexed_files", 0),
            failed_files=d.get("failed_files", 0),
            total_symbols=d.get("total_symbols", 0),
            total_imports=d.get("total_imports", 0),
            languages=d.get("languages", {}),
            duration_seconds=d.get("duration_seconds", 0.0),
            indexed_at=d.get("indexed_at", ""),
        )


@dataclass
class RepoIndex:
    """Índice estructural completo de un repositorio."""
    repo_name: str
    repo_path: str        # path absoluto en disco al momento de la indexación
    files: list           # list[FileIndex]
    stats: IndexStats

    def to_dict(self) -> dict:
        return {
            "repo_name": self.repo_name,
            "repo_path": self.repo_path,
            "files": [f.to_dict() for f in self.files],
            "stats": self.stats.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RepoIndex":
        return cls(
            repo_name=d["repo_name"],
            repo_path=d["repo_path"],
            files=[FileIndex.from_dict(f) for f in d.get("files", [])],
            stats=IndexStats.from_dict(d.get("stats", {})),
        )

    def get_file(self, rel_path: str) -> Optional[FileIndex]:
        for f in self.files:
            if f.path == rel_path:
                return f
        return None

    def symbols_by_kind(self, kind: str) -> list:
        """Retorna [(file_path, Symbol)] para un kind dado."""
        return [
            (f.path, s)
            for f in self.files
            for s in f.symbols
            if s.kind == kind
        ]

    def files_by_language(self, language: str) -> list:
        """Retorna todos los FileIndex de un lenguaje dado."""
        return [f for f in self.files if f.language == language]
