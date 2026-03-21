"""
Tests para cipher.index — parsers, indexer y schema serialization.
"""

import os
import json
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cipher.index.schema import Import, Symbol, FileIndex, IndexStats, RepoIndex
from cipher.index.parsers.python import PythonParser
from cipher.index.parsers.typescript import TypeScriptParser
from cipher.index.parsers.go import GoParser
from cipher.index.parsers.registry import get_parser, supported_extensions, supported_languages
from cipher.index.indexer import RepoIndexer


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def write_file(tmp_path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


# ─── Schema serialization ─────────────────────────────────────────────────────

class TestSchemaSerialize:
    def test_import_roundtrip(self):
        imp = Import(module="os.path", names=["join", "exists"], alias=None, is_relative=False, line=1)
        assert Import.from_dict(imp.to_dict()) == imp

    def test_import_relative_roundtrip(self):
        imp = Import(module=".utils", names=["helper"], alias=None, is_relative=True, line=5)
        assert Import.from_dict(imp.to_dict()) == imp

    def test_symbol_roundtrip(self):
        sym = Symbol(name="MyClass", kind="class", line=10, parent=None, decorators=["dataclass"])
        assert Symbol.from_dict(sym.to_dict()) == sym

    def test_symbol_method_roundtrip(self):
        sym = Symbol(name="my_method", kind="method", line=20, parent="MyClass", decorators=[])
        assert Symbol.from_dict(sym.to_dict()) == sym

    def test_file_index_roundtrip(self, tmp_path):
        fi = FileIndex(
            path="src/app.py",
            language="python",
            imports=[Import(module="os", names=[], alias=None, is_relative=False, line=1)],
            symbols=[Symbol(name="App", kind="class", line=5, parent=None, decorators=[])],
            parse_error=None,
            size_bytes=100,
            lines=20,
        )
        assert FileIndex.from_dict(fi.to_dict()) == fi

    def test_repo_index_full_roundtrip(self, tmp_path):
        fi = FileIndex(
            path="main.py", language="python",
            imports=[], symbols=[], parse_error=None, size_bytes=50, lines=5,
        )
        stats = IndexStats(
            total_files=1, indexed_files=1, failed_files=0,
            total_symbols=0, total_imports=0, languages={"python": 1},
            duration_seconds=0.1, indexed_at="2026-01-01T00:00:00+00:00",
        )
        ri = RepoIndex(repo_name="myrepo", repo_path="/some/path", files=[fi], stats=stats)
        restored = RepoIndex.from_dict(ri.to_dict())
        assert restored.repo_name == ri.repo_name
        assert len(restored.files) == 1
        assert restored.files[0].path == "main.py"

    def test_file_index_with_parse_error_roundtrip(self):
        fi = FileIndex(
            path="broken.py", language="python",
            imports=[], symbols=[],
            parse_error="SyntaxError: invalid syntax",
            size_bytes=30, lines=3,
        )
        restored = FileIndex.from_dict(fi.to_dict())
        assert restored.parse_error == "SyntaxError: invalid syntax"


# ─── Python Parser ────────────────────────────────────────────────────────────

class TestPythonParser:
    def setup_method(self):
        self.parser = PythonParser()

    def test_parses_absolute_imports(self, tmp_path):
        path = write_file(tmp_path, "a.py", "import os\nimport sys\n")
        fi = self.parser.parse(path, "a.py")
        modules = [i.module for i in fi.imports]
        assert "os" in modules
        assert "sys" in modules
        assert all(not i.is_relative for i in fi.imports)

    def test_parses_from_imports(self, tmp_path):
        path = write_file(tmp_path, "b.py", "from os.path import join, exists\n")
        fi = self.parser.parse(path, "b.py")
        assert len(fi.imports) == 1
        assert fi.imports[0].module == "os.path"
        assert "join" in fi.imports[0].names
        assert "exists" in fi.imports[0].names

    def test_parses_relative_imports(self, tmp_path):
        path = write_file(tmp_path, "c.py", "from . import utils\nfrom ..models import User\n")
        fi = self.parser.parse(path, "c.py")
        rel = [i for i in fi.imports if i.is_relative]
        assert len(rel) == 2
        assert rel[0].module == ".utils" or rel[0].module.startswith(".")

    def test_parses_aliased_imports(self, tmp_path):
        path = write_file(tmp_path, "d.py", "import numpy as np\n")
        fi = self.parser.parse(path, "d.py")
        assert fi.imports[0].alias == "np"

    def test_parses_class(self, tmp_path):
        path = write_file(tmp_path, "e.py", "class MyClass:\n    pass\n")
        fi = self.parser.parse(path, "e.py")
        classes = [s for s in fi.symbols if s.kind == "class"]
        assert len(classes) == 1
        assert classes[0].name == "MyClass"
        assert classes[0].parent is None

    def test_parses_methods_in_class(self, tmp_path):
        code = "class Foo:\n    def bar(self):\n        pass\n    def baz(self):\n        pass\n"
        path = write_file(tmp_path, "f.py", code)
        fi = self.parser.parse(path, "f.py")
        methods = [s for s in fi.symbols if s.kind == "method"]
        assert len(methods) == 2
        assert all(m.parent == "Foo" for m in methods)

    def test_parses_top_level_function(self, tmp_path):
        path = write_file(tmp_path, "g.py", "def my_func(x):\n    return x\n")
        fi = self.parser.parse(path, "g.py")
        funcs = [s for s in fi.symbols if s.kind == "function"]
        assert len(funcs) == 1
        assert funcs[0].name == "my_func"
        assert funcs[0].parent is None

    def test_does_not_index_nested_functions(self, tmp_path):
        code = "def outer():\n    def inner():\n        pass\n"
        path = write_file(tmp_path, "h.py", code)
        fi = self.parser.parse(path, "h.py")
        names = [s.name for s in fi.symbols]
        assert "outer" in names
        assert "inner" not in names

    def test_parses_async_function(self, tmp_path):
        path = write_file(tmp_path, "i.py", "async def fetch(url):\n    pass\n")
        fi = self.parser.parse(path, "i.py")
        assert fi.symbols[0].kind == "function"
        assert fi.symbols[0].name == "fetch"

    def test_parses_decorators(self, tmp_path):
        code = "class Foo:\n    @staticmethod\n    def bar():\n        pass\n"
        path = write_file(tmp_path, "j.py", code)
        fi = self.parser.parse(path, "j.py")
        method = next(s for s in fi.symbols if s.kind == "method")
        assert "staticmethod" in method.decorators

    def test_returns_error_on_syntax_error(self, tmp_path):
        path = write_file(tmp_path, "bad.py", "def broken(\n")
        fi = self.parser.parse(path, "bad.py")
        assert fi.parse_error is not None
        assert "SyntaxError" in fi.parse_error
        assert fi.imports == []
        assert fi.symbols == []

    def test_returns_error_on_missing_file(self, tmp_path):
        fi = self.parser.parse("/nonexistent/path.py", "path.py")
        assert fi.parse_error is not None

    def test_no_exception_propagated(self, tmp_path):
        fi = self.parser.parse("/this/does/not/exist.py", "exist.py")
        assert isinstance(fi, FileIndex)  # no exception


# ─── TypeScript Parser ────────────────────────────────────────────────────────

class TestTypeScriptParser:
    def setup_method(self):
        self.parser = TypeScriptParser()

    def test_parses_named_imports(self, tmp_path):
        code = "import { useState, useEffect } from 'react';\n"
        path = write_file(tmp_path, "a.ts", code)
        fi = self.parser.parse(path, "a.ts")
        assert len(fi.imports) == 1
        assert fi.imports[0].module == "react"
        assert "useState" in fi.imports[0].names

    def test_parses_multiline_named_imports(self, tmp_path):
        code = "import {\n  useState,\n  useEffect,\n} from 'react';\n"
        path = write_file(tmp_path, "b.ts", code)
        fi = self.parser.parse(path, "b.ts")
        assert any(i.module == "react" for i in fi.imports)

    def test_parses_default_import(self, tmp_path):
        code = "import React from 'react';\n"
        path = write_file(tmp_path, "c.ts", code)
        fi = self.parser.parse(path, "c.ts")
        assert fi.imports[0].module == "react"
        assert "React" in fi.imports[0].names

    def test_parses_namespace_import(self, tmp_path):
        code = "import * as path from 'path';\n"
        path = write_file(tmp_path, "d.ts", code)
        fi = self.parser.parse(path, "d.ts")
        assert any("* as path" in " ".join(i.names) for i in fi.imports)

    def test_parses_require_commonjs(self, tmp_path):
        code = "const express = require('express');\n"
        path = write_file(tmp_path, "e.js", code)
        fi = self.parser.parse(path, "e.js")
        assert any(i.module == "express" for i in fi.imports)

    def test_relative_imports_detected(self, tmp_path):
        code = "import { helper } from './utils';\n"
        path = write_file(tmp_path, "f.ts", code)
        fi = self.parser.parse(path, "f.ts")
        assert fi.imports[0].is_relative is True

    def test_parses_class_declaration(self, tmp_path):
        code = "export class UserService {\n}\n"
        path = write_file(tmp_path, "g.ts", code)
        fi = self.parser.parse(path, "g.ts")
        classes = [s for s in fi.symbols if s.kind == "class"]
        assert any(c.name == "UserService" for c in classes)

    def test_parses_interface_declaration(self, tmp_path):
        code = "export interface IUser {\n  id: number;\n}\n"
        path = write_file(tmp_path, "h.ts", code)
        fi = self.parser.parse(path, "h.ts")
        ifaces = [s for s in fi.symbols if s.kind == "interface"]
        assert any(i.name == "IUser" for i in ifaces)

    def test_parses_function_declaration(self, tmp_path):
        code = "export async function fetchUser(id: number) {\n}\n"
        path = write_file(tmp_path, "i.ts", code)
        fi = self.parser.parse(path, "i.ts")
        funcs = [s for s in fi.symbols if s.kind == "function"]
        assert any(f.name == "fetchUser" for f in funcs)

    def test_parses_arrow_function_const(self, tmp_path):
        code = "export const myHandler = (req: Request) => {\n};\n"
        path = write_file(tmp_path, "j.ts", code)
        fi = self.parser.parse(path, "j.ts")
        funcs = [s for s in fi.symbols if s.kind == "function"]
        assert any(f.name == "myHandler" for f in funcs)

    def test_non_relative_import(self, tmp_path):
        code = "import axios from 'axios';\n"
        path = write_file(tmp_path, "k.ts", code)
        fi = self.parser.parse(path, "k.ts")
        assert fi.imports[0].is_relative is False


# ─── Go Parser ────────────────────────────────────────────────────────────────

class TestGoParser:
    def setup_method(self):
        self.parser = GoParser()

    def test_parses_single_import(self, tmp_path):
        code = 'package main\n\nimport "fmt"\n'
        path = write_file(tmp_path, "a.go", code)
        fi = self.parser.parse(path, "a.go")
        assert any(i.module == "fmt" for i in fi.imports)

    def test_parses_import_block(self, tmp_path):
        code = 'package main\n\nimport (\n\t"fmt"\n\t"os"\n)\n'
        path = write_file(tmp_path, "b.go", code)
        fi = self.parser.parse(path, "b.go")
        modules = [i.module for i in fi.imports]
        assert "fmt" in modules
        assert "os" in modules

    def test_parses_aliased_import(self, tmp_path):
        code = 'import (\n\tlog "github.com/sirupsen/logrus"\n)\n'
        path = write_file(tmp_path, "c.go", code)
        fi = self.parser.parse(path, "c.go")
        aliased = [i for i in fi.imports if i.alias == "log"]
        assert len(aliased) == 1
        assert aliased[0].module == "github.com/sirupsen/logrus"

    def test_parses_blank_import(self, tmp_path):
        code = 'import (\n\t_ "github.com/lib/pq"\n)\n'
        path = write_file(tmp_path, "d.go", code)
        fi = self.parser.parse(path, "d.go")
        assert any(i.alias == "_" for i in fi.imports)

    def test_parses_top_level_func(self, tmp_path):
        code = "package main\n\nfunc main() {\n}\n"
        path = write_file(tmp_path, "e.go", code)
        fi = self.parser.parse(path, "e.go")
        funcs = [s for s in fi.symbols if s.kind == "function"]
        assert any(f.name == "main" for f in funcs)

    def test_parses_method_with_receiver(self, tmp_path):
        code = "func (s *UserService) GetUser(id int) User {\n\treturn User{}\n}\n"
        path = write_file(tmp_path, "f.go", code)
        fi = self.parser.parse(path, "f.go")
        methods = [s for s in fi.symbols if s.kind == "method"]
        assert len(methods) == 1
        assert methods[0].name == "GetUser"
        assert methods[0].parent == "UserService"

    def test_parses_struct(self, tmp_path):
        code = "type User struct {\n\tID int\n\tName string\n}\n"
        path = write_file(tmp_path, "g.go", code)
        fi = self.parser.parse(path, "g.go")
        structs = [s for s in fi.symbols if s.kind == "struct"]
        assert any(s.name == "User" for s in structs)

    def test_parses_interface(self, tmp_path):
        code = "type Repository interface {\n\tFind(id int) error\n}\n"
        path = write_file(tmp_path, "h.go", code)
        fi = self.parser.parse(path, "h.go")
        ifaces = [s for s in fi.symbols if s.kind == "interface"]
        assert any(i.name == "Repository" for i in ifaces)

    def test_go_imports_are_never_relative(self, tmp_path):
        code = 'import "fmt"\n'
        path = write_file(tmp_path, "i.go", code)
        fi = self.parser.parse(path, "i.go")
        assert all(not i.is_relative for i in fi.imports)


# ─── Parser Registry ──────────────────────────────────────────────────────────

class TestParserRegistry:
    def test_python_extension_registered(self):
        assert get_parser(".py") is not None
        assert get_parser(".py").language == "python"

    def test_typescript_extensions_registered(self):
        for ext in (".ts", ".tsx", ".js", ".jsx"):
            assert get_parser(ext) is not None
            assert get_parser(ext).language == "typescript"

    def test_go_extension_registered(self):
        assert get_parser(".go") is not None
        assert get_parser(".go").language == "go"

    def test_unknown_extension_returns_none(self):
        assert get_parser(".xyz") is None
        assert get_parser(".css") is None
        assert get_parser(".md") is None

    def test_case_insensitive(self):
        assert get_parser(".PY") is not None
        assert get_parser(".TS") is not None

    def test_supported_languages(self):
        langs = supported_languages()
        assert "python" in langs
        assert "typescript" in langs
        assert "go" in langs


# ─── RepoIndexer ──────────────────────────────────────────────────────────────

class TestRepoIndexer:
    def _make_repo(self, tmp_path):
        """Crea un repo de prueba con archivos de múltiples lenguajes."""
        (tmp_path / "main.py").write_text(
            "import os\nfrom pathlib import Path\n\nclass App:\n    def run(self):\n        pass\n",
            encoding="utf-8",
        )
        (tmp_path / "utils.ts").write_text(
            "import { readFile } from 'fs';\n\nexport function loadConfig() {\n}\n",
            encoding="utf-8",
        )
        (tmp_path / "server.go").write_text(
            'package main\n\nimport "net/http"\n\nfunc main() {\n}\n',
            encoding="utf-8",
        )
        return tmp_path

    def test_indexes_mixed_repo(self, tmp_path):
        repo = self._make_repo(tmp_path)
        indexer = RepoIndexer(str(repo))
        ri = indexer.index()
        assert ri.stats.total_files == 3
        assert ri.stats.indexed_files == 3
        assert ri.stats.failed_files == 0

    def test_stats_count_per_language(self, tmp_path):
        repo = self._make_repo(tmp_path)
        indexer = RepoIndexer(str(repo))
        ri = indexer.index()
        assert ri.stats.languages.get("python") == 1
        assert ri.stats.languages.get("typescript") == 1
        assert ri.stats.languages.get("go") == 1

    def test_symbols_extracted(self, tmp_path):
        repo = self._make_repo(tmp_path)
        indexer = RepoIndexer(str(repo))
        ri = indexer.index()
        assert ri.stats.total_symbols > 0

    def test_ignores_node_modules(self, tmp_path):
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "lodash.js").write_text("export function merge() {}", encoding="utf-8")
        (tmp_path / "app.ts").write_text("import { x } from './y';\n", encoding="utf-8")
        indexer = RepoIndexer(str(tmp_path))
        ri = indexer.index()
        paths = [f.path for f in ri.files]
        assert not any("node_modules" in p for p in paths)

    def test_ignores_pycache(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "module.cpython-312.pyc").write_text("", encoding="utf-8")
        (tmp_path / "app.py").write_text("import os\n", encoding="utf-8")
        indexer = RepoIndexer(str(tmp_path))
        ri = indexer.index()
        paths = [f.path for f in ri.files]
        assert not any("__pycache__" in p for p in paths)

    def test_parse_error_does_not_interrupt_indexing(self, tmp_path):
        (tmp_path / "good.py").write_text("import os\n", encoding="utf-8")
        (tmp_path / "bad.py").write_text("def broken(\n", encoding="utf-8")
        indexer = RepoIndexer(str(tmp_path))
        ri = indexer.index()
        assert ri.stats.total_files == 2
        assert ri.stats.failed_files == 1
        assert ri.stats.indexed_files == 1

    def test_save_and_load_roundtrip(self, tmp_path):
        repo = self._make_repo(tmp_path)
        indexer = RepoIndexer(str(repo))
        ri = indexer.index()
        output_dir = str(tmp_path / "index_output")
        index_path = indexer.save(ri, output_dir)
        assert os.path.exists(index_path)
        loaded = RepoIndexer.load(index_path)
        assert loaded.repo_name == ri.repo_name
        assert len(loaded.files) == len(ri.files)
        assert loaded.stats.total_symbols == ri.stats.total_symbols

    def test_rel_paths_use_forward_slashes(self, tmp_path):
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "app.py").write_text("import os\n", encoding="utf-8")
        indexer = RepoIndexer(str(tmp_path))
        ri = indexer.index()
        for f in ri.files:
            assert "\\" not in f.path

    def test_get_file_by_path(self, tmp_path):
        repo = self._make_repo(tmp_path)
        indexer = RepoIndexer(str(repo))
        ri = indexer.index()
        fi = ri.get_file("main.py")
        assert fi is not None
        assert fi.language == "python"

    def test_symbols_by_kind(self, tmp_path):
        repo = self._make_repo(tmp_path)
        indexer = RepoIndexer(str(repo))
        ri = indexer.index()
        classes = ri.symbols_by_kind("class")
        assert any(sym.name == "App" for _, sym in classes)

    def test_empty_repo_returns_zero_stats(self, tmp_path):
        indexer = RepoIndexer(str(tmp_path))
        ri = indexer.index()
        assert ri.stats.total_files == 0
        assert ri.stats.total_symbols == 0
