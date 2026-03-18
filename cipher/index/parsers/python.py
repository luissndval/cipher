"""
cipher index — Python Parser
Extrae imports y símbolos de archivos .py usando el módulo ast de stdlib.
Determinístico: no depende de LLM.
"""

import ast

from cipher.index.schema import FileIndex, Import, Symbol
from cipher.index.parsers.base import LanguageParser


class _SymbolVisitor(ast.NodeVisitor):
    """
    Extrae clases, funciones top-level y métodos de clase.
    No desciende dentro de funciones → ignora funciones anidadas (intencional).
    """

    def __init__(self):
        self.symbols: list[Symbol] = []
        self._class_stack: list[str] = []

    def _get_decorators(self, node) -> list:
        result = []
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                result.append(d.id)
            elif isinstance(d, ast.Attribute):
                result.append(d.attr)
            elif isinstance(d, ast.Call):
                if isinstance(d.func, ast.Name):
                    result.append(d.func.id)
                elif isinstance(d.func, ast.Attribute):
                    result.append(d.func.attr)
        return result

    def visit_ClassDef(self, node: ast.ClassDef):
        self.symbols.append(Symbol(
            name=node.name,
            kind="class",
            line=node.lineno,
            parent=None,
            decorators=self._get_decorators(node),
        ))
        self._class_stack.append(node.name)
        self.generic_visit(node)   # descender para encontrar métodos
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        kind = "method" if self._class_stack else "function"
        parent = self._class_stack[-1] if self._class_stack else None
        self.symbols.append(Symbol(
            name=node.name,
            kind=kind,
            line=node.lineno,
            parent=parent,
            decorators=self._get_decorators(node),
        ))
        # NO llamar generic_visit → no descender dentro de funciones

    # Manejar async def igual que def
    visit_AsyncFunctionDef = visit_FunctionDef


class PythonParser(LanguageParser):
    language = "python"
    extensions = (".py",)

    def parse(self, abs_path: str, rel_path: str) -> FileIndex:
        content = self._safe_read(abs_path)
        if content is None:
            return self._make_error(rel_path, "No se pudo leer el archivo (encoding o permisos)")

        size_bytes = len(content.encode("utf-8", errors="replace"))
        lines = self._count_lines(content)

        try:
            tree = ast.parse(content, filename=abs_path)
        except SyntaxError as e:
            return self._make_error(rel_path, f"SyntaxError: {e}", size_bytes, lines)
        except Exception as e:
            return self._make_error(rel_path, str(e), size_bytes, lines)

        imports = self._extract_imports(tree)
        symbols = self._extract_symbols(tree)

        return FileIndex(
            path=rel_path,
            language=self.language,
            imports=imports,
            symbols=symbols,
            parse_error=None,
            size_bytes=size_bytes,
            lines=lines,
        )

    def _extract_imports(self, tree: ast.Module) -> list:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(Import(
                        module=alias.name,
                        names=[],
                        alias=alias.asname,
                        is_relative=False,
                        line=node.lineno,
                    ))
            elif isinstance(node, ast.ImportFrom):
                level = node.level  # 0=absoluto, 1=., 2=..
                module = node.module or ""
                if level > 0:
                    module = ("." * level) + module
                imports.append(Import(
                    module=module,
                    names=[alias.name for alias in node.names],
                    alias=None,
                    is_relative=(level > 0),
                    line=node.lineno,
                ))
        return imports

    def _extract_symbols(self, tree: ast.Module) -> list:
        visitor = _SymbolVisitor()
        visitor.visit(tree)
        return visitor.symbols
