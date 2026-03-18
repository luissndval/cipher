"""
cipher index — Go Parser
Extrae imports y símbolos de archivos .go usando regex.

Soporta:
  Imports: single, block, aliased, blank (_)
  Symbols: func (top-level y métodos con receiver), struct, interface

Limitaciones conocidas (Fase 1):
  - No extrae campos de struct ni firmas de métodos de interface
  - Los comentarios pueden interferir con algunos patterns
"""

import re

from cipher.index.schema import FileIndex, Import, Symbol
from cipher.index.parsers.base import LanguageParser


class GoParser(LanguageParser):
    language = "go"
    extensions = (".go",)

    def parse(self, abs_path: str, rel_path: str) -> FileIndex:
        content = self._safe_read(abs_path)
        if content is None:
            return self._make_error(rel_path, "No se pudo leer el archivo")

        size_bytes = len(content.encode("utf-8", errors="replace"))
        lines = self._count_lines(content)

        imports = self._extract_imports(content)
        symbols = self._extract_symbols(content)

        return FileIndex(
            path=rel_path,
            language=self.language,
            imports=imports,
            symbols=symbols,
            parse_error=None,
            size_bytes=size_bytes,
            lines=lines,
        )

    def _extract_imports(self, content: str) -> list:
        imports = []
        lines = content.split("\n")
        in_block = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Dentro del bloque import ( ... )
            if in_block:
                if stripped == ")":
                    in_block = False
                    continue
                # blank import: _ "pkg"
                m = re.match(r'^_\s+"([^"]+)"', stripped)
                if m:
                    imports.append(Import(module=m.group(1), names=[], alias="_", is_relative=False, line=i))
                    continue
                # aliased: alias "pkg"
                m = re.match(r'^(\w+)\s+"([^"]+)"', stripped)
                if m:
                    imports.append(Import(module=m.group(2), names=[], alias=m.group(1), is_relative=False, line=i))
                    continue
                # plain: "pkg"
                m = re.match(r'^"([^"]+)"', stripped)
                if m:
                    imports.append(Import(module=m.group(1), names=[], alias=None, is_relative=False, line=i))
                continue

            # Inicio de bloque: import (
            if re.match(r"^import\s*\(", stripped):
                in_block = True
                continue

            # Single aliased: import alias "pkg"
            m = re.match(r'^import\s+(\w+)\s+"([^"]+)"', stripped)
            if m:
                imports.append(Import(module=m.group(2), names=[], alias=m.group(1), is_relative=False, line=i))
                continue

            # Single: import "pkg"
            m = re.match(r'^import\s+"([^"]+)"', stripped)
            if m:
                imports.append(Import(module=m.group(1), names=[], alias=None, is_relative=False, line=i))

        return imports

    def _extract_symbols(self, content: str) -> list:
        symbols = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Método con receiver: func (r *ReceiverType) MethodName(
            m = re.match(r"^func\s+\(\s*\w+\s+\*?(\w+)\s*\)\s+(\w+)\s*\(", stripped)
            if m:
                symbols.append(Symbol(
                    name=m.group(2),
                    kind="method",
                    line=i,
                    parent=m.group(1),
                    decorators=[],
                ))
                continue

            # Función top-level: func FuncName(
            m = re.match(r"^func\s+(\w+)\s*\(", stripped)
            if m:
                symbols.append(Symbol(
                    name=m.group(1),
                    kind="function",
                    line=i,
                    parent=None,
                    decorators=[],
                ))
                continue

            # Struct: type Name struct
            m = re.match(r"^type\s+(\w+)\s+struct\b", stripped)
            if m:
                symbols.append(Symbol(
                    name=m.group(1),
                    kind="struct",
                    line=i,
                    parent=None,
                    decorators=[],
                ))
                continue

            # Interface: type Name interface
            m = re.match(r"^type\s+(\w+)\s+interface\b", stripped)
            if m:
                symbols.append(Symbol(
                    name=m.group(1),
                    kind="interface",
                    line=i,
                    parent=None,
                    decorators=[],
                ))

        return symbols
