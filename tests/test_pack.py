"""
Tests — cipher pack (Fase 3)
Cubre: scorer, budget, PackBuilder, ContextPack serialization
"""

import os
import pytest

from cipher.index.schema import Import, Symbol, FileIndex, RepoIndex, IndexStats
from cipher.graph.schema import GraphNode, GraphEdge, DependencyGraph
from cipher.pack.schema import PackEntry, PackManifest, ContextPack
from cipher.pack.scorer import score_files, _task_tokens
from cipher.pack.budget import TokenBudget, estimate_tokens, trim_content, get_budget
from cipher.pack.builder import PackBuilder, _slugify


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_symbol(name: str, kind: str = "function") -> Symbol:
    return Symbol(name=name, kind=kind, line=1, parent=None, decorators=[])


def make_file(path: str, language: str = "python", symbols=None, imports=None) -> FileIndex:
    return FileIndex(
        path=path, language=language,
        imports=imports or [], symbols=symbols or [],
        parse_error=None, size_bytes=100, lines=10,
    )


def make_import(module: str, is_relative: bool = False) -> Import:
    return Import(module=module, is_relative=is_relative, names=[], alias=None, line=1)


def make_repo(*files: FileIndex, name: str = "test-repo") -> RepoIndex:
    return RepoIndex(
        repo_name=name,
        repo_path="/repo",
        files=list(files),
        stats=IndexStats(0, 0, 0, 0, 0, {}, 0.0, ""),
    )


def make_graph(*edges, nodes=None) -> DependencyGraph:
    if nodes is None:
        all_paths = set()
        for from_f, to_f in edges:
            all_paths.add(from_f); all_paths.add(to_f)
        nodes = {p: GraphNode(p, "python", 0) for p in all_paths}
    edge_objs = [GraphEdge(f, t, "import", []) for f, t in edges]
    return DependencyGraph("r", "/r", "", "0.3.0", nodes, edge_objs, {})


# ─── Schema serialization ─────────────────────────────────────────────────────

def test_pack_entry_to_dict():
    e = PackEntry(path="a.py", language="python", role="target",
                  score=2.5, tokens=100, content="x = 1")
    d = e.to_dict()
    assert d["path"] == "a.py"
    assert d["role"] == "target"
    assert "content" not in d  # content excluido intencionalmente


def test_pack_manifest_roundtrip():
    m = PackManifest(
        task_id="abc123", task_description="fix auth bug",
        repo_name="myrepo", repo_path="/repo",
        built_at="2024-01-01T00:00:00+00:00", brain_version="0.3.0",
        provider="claude", token_budget=60_000, tokens_used=5_000,
        files_included=[{"path": "a.py", "role": "target"}],
        context_pack_hash="deadbeef",
    )
    m2 = PackManifest.from_dict(m.to_dict())
    assert m2.task_id == m.task_id
    assert m2.tokens_used == m.tokens_used
    assert m2.context_pack_hash == m.context_pack_hash


# ─── Scorer ───────────────────────────────────────────────────────────────────

def test_task_tokens_filters_stopwords():
    tokens = _task_tokens("fix the auth bug in the login")
    assert "the" not in tokens
    assert "in" not in tokens
    assert "auth" in tokens
    assert "login" in tokens


def test_task_tokens_case_insensitive():
    tokens = _task_tokens("Fix AUTH Bug")
    assert "auth" in tokens
    assert "bug" in tokens


def test_score_path_match():
    files = [
        make_file("auth/login.py", symbols=[make_symbol("login")]),
        make_file("utils/helper.py", symbols=[make_symbol("help")]),
    ]
    scored = score_files(files, "fix auth login bug")
    # auth/login.py debe tener mayor score
    top_path = scored[0][1].path
    assert top_path == "auth/login.py"


def test_score_symbol_match():
    files = [
        make_file("a.py", symbols=[make_symbol("UserAuthenticator")]),
        make_file("b.py", symbols=[make_symbol("DataProcessor")]),
    ]
    scored = score_files(files, "fix authenticator timeout")
    assert scored[0][1].path == "a.py"


def test_score_all_zero_returns_all():
    files = [make_file("a.py"), make_file("b.py")]
    scored = score_files(files, "the a an in")
    assert len(scored) == 2


def test_score_with_graph_high_inbound():
    # b.py is imported by many files → high inbound
    files = [make_file("a.py"), make_file("b.py")]
    nodes = {"a.py": GraphNode("a.py", "python", 0), "b.py": GraphNode("b.py", "python", 0)}
    edges = [
        GraphEdge("x.py", "b.py", "import", []),
        GraphEdge("y.py", "b.py", "import", []),
        GraphEdge("z.py", "b.py", "import", []),
    ]
    nodes["x.py"] = GraphNode("x.py", "python", 0)
    nodes["y.py"] = GraphNode("y.py", "python", 0)
    nodes["z.py"] = GraphNode("z.py", "python", 0)
    graph = DependencyGraph("r", "/r", "", "0.3.0", nodes, edges, {})
    # b.py tiene 3 inbound; con solo 2 files en index el threshold puede variar
    scored = score_files(files, "some task", graph)
    scores_by_path = {f.path: s for s, f in scored}
    # b.py debería tener bonus de high_inbound o al menos no menos que a.py
    assert scores_by_path["b.py"] >= scores_by_path["a.py"]


# ─── Budget ───────────────────────────────────────────────────────────────────

def test_get_budget_claude():
    assert get_budget("claude") == 60_000


def test_get_budget_gemini():
    assert get_budget("gemini") == 400_000


def test_get_budget_unknown():
    assert get_budget("openai") == 60_000


def test_estimate_tokens():
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 400) == 100


def test_trim_content_no_trim_needed():
    text = "short content"
    result, used = trim_content(text, 1000)
    assert result == text
    assert used == estimate_tokens(text)


def test_trim_content_truncates():
    text = "x" * 1000
    result, used = trim_content(text, 10)  # max 40 chars
    assert "[truncado por budget]" in result
    assert used <= 20


def test_budget_reserve():
    b = TokenBudget("claude")
    assert b.reserve(100)
    assert b.used == 100
    assert b.remaining == 60_000 - 100


def test_budget_reserve_exceeds():
    b = TokenBudget("claude")
    assert not b.reserve(60_001)
    assert b.used == 0


def test_budget_allocate():
    b = TokenBudget("claude")
    content = "a" * 400  # ~100 tokens
    trimmed, used = b.allocate(content)
    assert used == 100
    assert b.remaining == 60_000 - 100


def test_budget_allocate_respects_cap():
    b = TokenBudget("claude")
    content = "a" * 4000  # ~1000 tokens
    trimmed, used = b.allocate(content, max_tokens=50)
    assert used <= 60  # puede ser ligeramente más por overhead del mensaje truncado


def test_budget_files_ratio():
    b = TokenBudget("claude")
    assert b.files_budget() == int(60_000 * 0.90)


# ─── PackBuilder ──────────────────────────────────────────────────────────────

def _make_builder_with_files(tmp_path, files_content: dict) -> tuple:
    """
    Crea un builder con archivos reales en disco.
    files_content: {rel_path: content}
    """
    repo_path = str(tmp_path / "repo")
    os.makedirs(repo_path)

    file_indexes = []
    for rel_path, content in files_content.items():
        full = os.path.join(repo_path, rel_path.replace("/", os.sep))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        file_indexes.append(make_file(rel_path, symbols=[make_symbol(rel_path.split("/")[-1].split(".")[0])]))

    repo_index = make_repo(*file_indexes)
    nodes = {f.path: GraphNode(f.path, "python", 0) for f in file_indexes}
    graph = DependencyGraph("test-repo", repo_path, "", "0.3.0", nodes, [], {})

    builder = PackBuilder(repo_index, graph, repo_path)
    return builder, repo_path


def test_builder_creates_pack(tmp_path):
    builder, _ = _make_builder_with_files(tmp_path, {
        "auth/login.py": "def login(): pass",
        "utils/helper.py": "def help(): pass",
    })
    pack = builder.build("fix login authentication")
    assert pack.manifest.task_description == "fix login authentication"
    assert pack.manifest.repo_name == "test-repo"
    assert len(pack.entries) > 0


def test_builder_targets_relevant_file(tmp_path):
    builder, _ = _make_builder_with_files(tmp_path, {
        "auth/login.py": "def login(): pass",
        "utils/helper.py": "def help(): pass",
    })
    pack = builder.build("fix login bug")
    target_paths = [e.path for e in pack.entries if e.role == "target"]
    assert "auth/login.py" in target_paths


def test_builder_includes_dependencies(tmp_path):
    repo_path = str(tmp_path / "repo")
    os.makedirs(repo_path)

    for rel, content in {
        "auth/login.py": "from auth import models\ndef login(): pass",
        "auth/models.py": "class User: pass",
    }.items():
        full = os.path.join(repo_path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    login_fi = FileIndex(
        path="auth/login.py", language="python",
        imports=[make_import(".models", is_relative=True)],
        symbols=[make_symbol("login")],
        parse_error=None, size_bytes=50, lines=2,
    )
    # models_fi no tiene símbolos → score=0 por sí sola; solo entra via expansión de dependencias
    models_fi = FileIndex(
        path="auth/models.py", language="python",
        imports=[], symbols=[],
        parse_error=None, size_bytes=50, lines=5,
    )
    repo_index = make_repo(login_fi, models_fi)

    nodes = {
        "auth/login.py": GraphNode("auth/login.py", "python", 1),
        "auth/models.py": GraphNode("auth/models.py", "python", 1),
    }
    edges = [GraphEdge("auth/login.py", "auth/models.py", "import", [])]
    graph = DependencyGraph("test-repo", repo_path, "", "0.3.0", nodes, edges, {})

    builder = PackBuilder(repo_index, graph, repo_path)
    pack = builder.build("fix login authentication")

    all_paths = {e.path for e in pack.entries}
    # login.py es target, models.py debe ser dependency
    assert "auth/login.py" in all_paths
    assert "auth/models.py" in all_paths

    dep_roles = {e.path: e.role for e in pack.entries}
    assert dep_roles.get("auth/models.py") == "dependency"


def test_builder_pack_has_hash(tmp_path):
    builder, _ = _make_builder_with_files(tmp_path, {"a.py": "x = 1"})
    pack = builder.build("any task")
    assert len(pack.manifest.context_pack_hash) == 64  # SHA-256 hex


def test_builder_provider_sets_budget(tmp_path):
    builder, _ = _make_builder_with_files(tmp_path, {"a.py": "x = 1"})
    pack_claude = builder.build("fix bug", provider="claude")
    pack_gemini = builder.build("fix bug", provider="gemini")
    assert pack_claude.manifest.token_budget == 60_000
    assert pack_gemini.manifest.token_budget == 400_000


def test_builder_save_creates_files(tmp_path):
    builder, _ = _make_builder_with_files(tmp_path, {"a.py": "x = 1"})
    pack = builder.build("any task")
    out_dir = str(tmp_path / "packs")
    md_path, manifest_path = PackBuilder.save(pack, out_dir)

    assert os.path.exists(md_path)
    assert os.path.exists(manifest_path)


def test_builder_save_md_content(tmp_path):
    builder, _ = _make_builder_with_files(tmp_path, {"auth/login.py": "def login(): pass"})
    pack = builder.build("fix login")
    out_dir = str(tmp_path / "packs")
    md_path, _ = PackBuilder.save(pack, out_dir)

    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    assert "Context Pack" in content
    assert "fix login" in content
    assert "auth/login.py" in content


def test_builder_load_manifest(tmp_path):
    builder, _ = _make_builder_with_files(tmp_path, {"a.py": "x = 1"})
    pack = builder.build("any task", task_id="test001")
    out_dir = str(tmp_path / "packs")
    _, manifest_path = PackBuilder.save(pack, out_dir)

    loaded = PackBuilder.load_manifest(manifest_path)
    assert loaded.task_id == "test001"
    assert loaded.repo_name == "test-repo"


def test_builder_no_relevant_files_still_returns_pack(tmp_path):
    builder, _ = _make_builder_with_files(tmp_path, {"a.py": "x = 1"})
    pack = builder.build("xyzzy completely irrelevant gibberish")
    assert pack.manifest is not None
    # Puede tener 0 entries si nada tiene score > 0


def test_slugify():
    assert _slugify("Fix auth bug") == "fix_auth_bug"
    assert _slugify("") == ""
    assert _slugify("  spaces  ") == "spaces"
