"""
cipher index — TypeScript/JavaScript Parser
Extrae imports y símbolos de archivos .ts/.tsx/.js/.jsx usando regex.

Soporta:
  Imports: ES modules (named, default, namespace, side-effect), CommonJS require()
  Symbols: class, interface, function, arrow function const

Limitaciones conocidas (Fase 1):
  - Imports condicionales (dentro de if) pueden no detectarse
  - Decorators TypeScript no se extraen todavía
  - Los métodos dentro de clases no se detectan (sin AST real)
"""

import re

from cipher.index.schema import FileIndex, Import, Symbol
from cipher.index.parsers.base import LanguageParser


class TypeScriptParser(LanguageParser):
    language = "typescript"
    extensions = (".ts", ".tsx", ".js", ".jsx")

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

    def _line_of(self, content: str, pos: int) -> int:
        return content[:pos].count("\n") + 1

    def _extract_imports(self, content: str) -> list:
        imports = []
        seen: set[tuple] = set()

        def add(module, names, alias, line):
            key = (module, line)
            if key not in seen:
                seen.add(key)
                imports.append(Import(
                    module=module,
                    names=names,
                    alias=alias,
                    is_relative=module.startswith("."),
                    line=line,
                ))

        # Named imports (multi-line safe): import { x, y } from '...'
        for m in re.finditer(
            r"import\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]",
            content, re.DOTALL
        ):
            names = [
                n.strip().split(" as ")[0].strip()
                for n in m.group(1).split(",")
                if n.strip()
            ]
            add(m.group(2), names, None, self._line_of(content, m.start()))

        # Default import: import X from '...'
        for m in re.finditer(
            r"import\s+(\w+)\s+from\s*['\"]([^'\"]+)['\"]", content
        ):
            add(m.group(2), [m.group(1)], None, self._line_of(content, m.start()))

        # Namespace import: import * as X from '...'
        for m in re.finditer(
            r"import\s+\*\s+as\s+(\w+)\s+from\s*['\"]([^'\"]+)['\"]", content
        ):
            add(m.group(2), [f"* as {m.group(1)}"], None, self._line_of(content, m.start()))

        # Side-effect import: import '...'
        for m in re.finditer(r"import\s+['\"]([^'\"]+)['\"]", content):
            add(m.group(1), [], None, self._line_of(content, m.start()))

        # CommonJS require: const X = require('...') or const { x, y } = require('...')
        for m in re.finditer(
            r"(?:const|let|var)\s+(?:\{([^}]+)\}|(\w+))\s*=\s*require\(['\"]([^'\"]+)['\"]\)",
            content,
        ):
            module = m.group(3)
            if m.group(1):
                names = [
                    n.strip().split(" as ")[0].strip()
                    for n in m.group(1).split(",")
                    if n.strip()
                ]
            else:
                names = [m.group(2)] if m.group(2) else []
            add(module, names, None, self._line_of(content, m.start()))

        return imports

    def _extract_symbols(self, content: str) -> list:
        symbols = []
        seen: set[tuple] = set()

        def add(name, kind, line):
            key = (name, line)
            if key not in seen:
                seen.add(key)
                symbols.append(Symbol(
                    name=name, kind=kind, line=line,
                    parent=None, decorators=[],
                ))

        # Class declarations
        for m in re.finditer(
            r"^(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)",
            content, re.MULTILINE,
        ):
            add(m.group(1), "class", self._line_of(content, m.start()))

        # Interface declarations
        for m in re.finditer(
            r"^(?:export\s+)?interface\s+(\w+)",
            content, re.MULTILINE,
        ):
            add(m.group(1), "interface", self._line_of(content, m.start()))

        # Named function declarations
        for m in re.finditer(
            r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)",
            content, re.MULTILINE,
        ):
            add(m.group(1), "function", self._line_of(content, m.start()))

        # Arrow function constants: export const myFn = (...) => or = async (...) =>
        for m in re.finditer(
            r"^(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(",
            content, re.MULTILINE,
        ):
            add(m.group(1), "function", self._line_of(content, m.start()))

        return symbols
