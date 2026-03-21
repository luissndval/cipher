"""
Tests — cipher graph (Fase 2)
Cubre: ImportResolver, GraphBuilder, DependencyGraph, impact set
"""

import pytest
from cipher.index.schema import Import, Symbol, FileIndex, RepoIndex, IndexStats
from cipher.graph.schema import GraphNode, GraphEdge, ImpactEntry, DependencyGraph
from cipher.graph.resolver import ImportResolver
from cipher.graph.builder import GraphBuilder


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_import(module: str, is_relative: bool = False, names=None) -> Import:
    return Import(module=module, is_relative=is_relative, names=names or [], alias=None, line=1)


def make_file(path: str, language: str, imports=None, symbols=None) -> FileIndex:
    return FileIndex(
        path=path,
        language=language,
        imports=imports or [],
        symbols=symbols or [],
        parse_error=None,
        size_bytes=0,
        lines=10,
    )


def make_repo(*files: FileIndex) -> RepoIndex:
    return RepoIndex(
        repo_name="test-repo",
        repo_path="/repo",
        files=list(files),
        stats=IndexStats(
            total_files=len(files),
            indexed_files=len(files),
            failed_files=0,
            total_symbols=0,
            total_imports=0,
            languages={},
            duration_seconds=0.0,
            indexed_at="",
        ),
    )


# ─── GraphNode / GraphEdge serialization ──────────────────────────────────────

def test_graph_node_roundtrip():
    node = GraphNode(path="a/b.py", language="python", symbol_count=3)
    assert GraphNode.from_dict(node.to_dict()) == node


def test_graph_edge_roundtrip():
    edge = GraphEdge(from_file="a.py", to_file="b.py", kind="import", names=["Foo"])
    assert GraphEdge.from_dict(edge.to_dict()) == edge


def test_impact_entry_roundtrip():
    entry = ImpactEntry(file_path="a.py", depth=2, via=["b.py"])
    assert ImpactEntry.from_dict(entry.to_dict()) == entry


def test_dependency_graph_roundtrip():
    g = DependencyGraph(
        repo_name="r", repo_path="/r", built_at="2024-01-01T00:00:00+00:00",
        brain_version="0.2.0",
        nodes={"a.py": GraphNode("a.py", "python", 1)},
        edges=[GraphEdge("a.py", "b.py", "import", ["X"])],
        external_imports={"os": 2},
    )
    g2 = DependencyGraph.from_dict(g.to_dict())
    assert g2.repo_name == g.repo_name
    assert len(g2.nodes) == 1
    assert len(g2.edges) == 1
    assert g2.external_imports == {"os": 2}


# ─── ImportResolver — Python relative ─────────────────────────────────────────

def test_resolver_python_relative_same_dir():
    known = {"pkg/utils.py", "pkg/models.py", "pkg/__init__.py"}
    r = ImportResolver(known)
    imp = make_import(".utils", is_relative=True)
    assert r.resolve(imp, "pkg/main.py", "python") == ["pkg/utils.py"]


def test_resolver_python_relative_parent():
    known = {"models.py", "pkg/views.py"}
    r = ImportResolver(known)
    imp = make_import("..models", is_relative=True)
    assert r.resolve(imp, "pkg/views.py", "python") == ["models.py"]


def test_resolver_python_relative_init():
    known = {"pkg/__init__.py"}
    r = ImportResolver(known)
    imp = make_import(".", is_relative=True)
    assert r.resolve(imp, "pkg/sub.py", "python") == ["pkg/__init__.py"]


def test_resolver_python_relative_package_init():
    known = {"pkg/sub/__init__.py"}
    r = ImportResolver(known)
    imp = make_import(".sub", is_relative=True)
    assert r.resolve(imp, "pkg/main.py", "python") == ["pkg/sub/__init__.py"]


def test_resolver_python_relative_too_many_dots():
    known = {"a.py"}
    r = ImportResolver(known)
    imp = make_import("....way.too.deep", is_relative=True)
    assert r.resolve(imp, "pkg/sub.py", "python") == []


def test_resolver_python_relative_not_found():
    known = {"pkg/other.py"}
    r = ImportResolver(known)
    imp = make_import(".missing", is_relative=True)
    assert r.resolve(imp, "pkg/main.py", "python") == []


# ─── ImportResolver — Python absolute ─────────────────────────────────────────

def test_resolver_python_absolute_found():
    known = {"cipher/index/schema.py"}
    r = ImportResolver(known)
    imp = make_import("cipher.index.schema", is_relative=False)
    assert r.resolve(imp, "any.py", "python") == ["cipher/index/schema.py"]


def test_resolver_python_absolute_init():
    known = {"cipher/__init__.py"}
    r = ImportResolver(known)
    imp = make_import("cipher", is_relative=False)
    assert r.resolve(imp, "any.py", "python") == ["cipher/__init__.py"]


def test_resolver_python_absolute_external():
    known = {"myapp/utils.py"}
    r = ImportResolver(known)
    imp = make_import("os.path", is_relative=False)
    assert r.resolve(imp, "any.py", "python") == []


# ─── ImportResolver — TypeScript ──────────────────────────────────────────────

def test_resolver_ts_relative_with_extension():
    known = {"src/utils.ts"}
    r = ImportResolver(known)
    imp = make_import("./utils", is_relative=True)
    assert r.resolve(imp, "src/index.ts", "typescript") == ["src/utils.ts"]


def test_resolver_ts_relative_tsx():
    known = {"src/Button.tsx"}
    r = ImportResolver(known)
    imp = make_import("./Button", is_relative=True)
    assert r.resolve(imp, "src/App.tsx", "typescript") == ["src/Button.tsx"]


def test_resolver_ts_relative_index():
    known = {"src/components/index.ts"}
    r = ImportResolver(known)
    imp = make_import("./components", is_relative=True)
    assert r.resolve(imp, "src/App.ts", "typescript") == ["src/components/index.ts"]


def test_resolver_ts_relative_parent_dir():
    known = {"src/shared/types.ts"}
    r = ImportResolver(known)
    imp = make_import("../shared/types", is_relative=True)
    assert r.resolve(imp, "src/api/client.ts", "typescript") == ["src/shared/types.ts"]


def test_resolver_ts_absolute_returns_none():
    known = {"react/index.ts"}
    r = ImportResolver(known)
    imp = make_import("react", is_relative=False)
    assert r.resolve(imp, "src/App.tsx", "typescript") == []


def test_resolver_go_always_none():
    known = {"internal/pkg/foo.go"}
    r = ImportResolver(known)
    imp = make_import("github.com/user/repo/internal/pkg", is_relative=False)
    assert r.resolve(imp, "main.go", "go") == []


# ─── GraphBuilder ──────────────────────────────────────────────────────────────

def test_builder_creates_nodes():
    repo = make_repo(
        make_file("a.py", "python"),
        make_file("b.py", "python"),
    )
    graph = GraphBuilder(repo).build()
    assert "a.py" in graph.nodes
    assert "b.py" in graph.nodes
    assert graph.node_count == 2


def test_builder_resolved_edge():
    repo = make_repo(
        make_file("pkg/a.py", "python", imports=[make_import(".b", is_relative=True, names=["Foo"])]),
        make_file("pkg/b.py", "python"),
    )
    graph = GraphBuilder(repo).build()
    assert graph.edge_count == 1
    e = graph.edges[0]
    assert e.from_file == "pkg/a.py"
    assert e.to_file == "pkg/b.py"
    assert e.names == ["Foo"]


def test_builder_external_import_counted():
    repo = make_repo(
        make_file("a.py", "python", imports=[make_import("os", is_relative=False)]),
    )
    graph = GraphBuilder(repo).build()
    assert graph.edge_count == 0
    assert graph.external_imports.get("os", 0) == 1


def test_builder_multiple_edges():
    repo = make_repo(
        make_file("a.py", "python", imports=[
            make_import(".b", is_relative=True),
            make_import(".c", is_relative=True),
        ]),
        make_file("b.py", "python"),
        make_file("c.py", "python"),
    )
    graph = GraphBuilder(repo).build()
    assert graph.edge_count == 2


def test_builder_metadata():
    repo = make_repo(make_file("a.py", "python"))
    graph = GraphBuilder(repo).build()
    assert graph.repo_name == "test-repo"
    assert graph.brain_version == "0.2.0"
    assert graph.built_at  # not empty


def test_builder_symbol_count_in_node():
    sym = Symbol(name="Foo", kind="class", line=1, parent=None, decorators=[])
    repo = make_repo(make_file("a.py", "python", symbols=[sym]))
    graph = GraphBuilder(repo).build()
    assert graph.nodes["a.py"].symbol_count == 1


# ─── DependencyGraph queries ───────────────────────────────────────────────────

def _simple_graph() -> DependencyGraph:
    """
    a → b → c
         ↓
          d
    """
    nodes = {p: GraphNode(p, "python", 0) for p in ["a.py", "b.py", "c.py", "d.py"]}
    edges = [
        GraphEdge("a.py", "b.py", "import", []),
        GraphEdge("b.py", "c.py", "import", []),
        GraphEdge("b.py", "d.py", "import", []),
    ]
    return DependencyGraph("r", "/r", "", "0.2.0", nodes, edges, {})


def test_dependencies_of():
    g = _simple_graph()
    assert set(g.dependencies_of("b.py")) == {"c.py", "d.py"}


def test_dependents_of():
    g = _simple_graph()
    assert g.dependents_of("b.py") == ["a.py"]


def test_edge_names():
    g = DependencyGraph("r", "/r", "", "0.2.0",
        nodes={"a.py": GraphNode("a.py", "python", 0), "b.py": GraphNode("b.py", "python", 0)},
        edges=[GraphEdge("a.py", "b.py", "import", ["Foo", "Bar"])],
        external_imports={},
    )
    assert set(g.edge_names("a.py", "b.py")) == {"Foo", "Bar"}


def test_impact_set_direct():
    g = _simple_graph()
    impact = g.impact_set("b.py")
    paths = [e.file_path for e in impact]
    assert "a.py" in paths


def test_impact_set_depth():
    g = _simple_graph()
    impact = g.impact_set("c.py")
    by_path = {e.file_path: e for e in impact}
    assert by_path["b.py"].depth == 1
    assert by_path["a.py"].depth == 2


def test_impact_set_via_chain():
    g = _simple_graph()
    impact = g.impact_set("c.py")
    by_path = {e.file_path: e for e in impact}
    # a.py is reached via c.py → b.py → a.py; via lists intermediaries: [c.py, b.py]
    assert by_path["a.py"].via == ["c.py", "b.py"]


def test_impact_set_unknown_file():
    g = _simple_graph()
    assert g.impact_set("unknown.py") == []


def test_impact_set_max_depth():
    # a → b → c → d (chain of 4)
    nodes = {p: GraphNode(p, "python", 0) for p in ["a.py", "b.py", "c.py", "d.py"]}
    edges = [
        GraphEdge("b.py", "a.py", "import", []),
        GraphEdge("c.py", "b.py", "import", []),
        GraphEdge("d.py", "c.py", "import", []),
    ]
    g = DependencyGraph("r", "/r", "", "0.2.0", nodes, edges, {})
    impact = g.impact_set("a.py", max_depth=2)
    paths = [e.file_path for e in impact]
    assert "b.py" in paths
    assert "c.py" in paths
    assert "d.py" not in paths


def test_isolated_files():
    g = _simple_graph()
    # Add isolated node
    g.nodes["z.py"] = GraphNode("z.py", "python", 0)
    assert "z.py" in g.isolated_files


def test_most_imported():
    g = _simple_graph()
    top = g.most_imported
    # b.py has 2 inbound edges (from a only — wait, only a→b)
    # c.py and d.py each have 1 (from b)
    counts = dict(top)
    assert counts["b.py"] == 1
    assert counts["c.py"] == 1


# ─── Save / Load ───────────────────────────────────────────────────────────────

def test_builder_save_load(tmp_path):
    repo = make_repo(
        make_file("pkg/a.py", "python", imports=[make_import(".b", is_relative=True)]),
        make_file("pkg/b.py", "python"),
    )
    graph = GraphBuilder(repo).build()
    saved = GraphBuilder.save(graph, str(tmp_path))
    loaded = GraphBuilder.load(saved)
    assert loaded.edge_count == graph.edge_count
    assert loaded.node_count == graph.node_count
    assert loaded.repo_name == graph.repo_name
