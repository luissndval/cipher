"""
cipher index — Base Parser
Contrato abstracto que todos los parsers de lenguaje deben implementar.
"""

from abc import ABC, abstractmethod
from cipher.index.schema import FileIndex


class LanguageParser(ABC):
    language: str         # "python" | "typescript" | "go"
    extensions: tuple     # (".py",) o (".ts", ".tsx")

    @abstractmethod
    def parse(self, abs_path: str, rel_path: str) -> FileIndex:
        """
        Parsea un archivo y retorna su FileIndex.
        CONTRATO: nunca propaga excepciones. Ante cualquier error,
        retorna FileIndex con parse_error=mensaje e imports/symbols vacíos.
        """
        ...

    def _safe_read(self, abs_path: str) -> str | None:
        """
        Lee el archivo probando distintos encodings.
        Retorna el contenido como str, o None si falla.
        Prueba utf-8-sig primero para manejar BOM en Windows.
        """
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                with open(abs_path, encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except OSError:
                return None
        return None

    def _count_lines(self, content: str) -> int:
        return content.count("\n") + 1 if content else 0

    def _make_error(
        self, rel_path: str, msg: str,
        size_bytes: int = 0, lines: int = 0
    ) -> FileIndex:
        return FileIndex(
            path=rel_path,
            language=self.language,
            imports=[],
            symbols=[],
            parse_error=msg,
            size_bytes=size_bytes,
            lines=lines,
        )
