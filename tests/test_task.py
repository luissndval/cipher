"""
Tests — cipher Task Engine (Fase 4)
Cubre: schema, store, analyzer, sources (manual/github/linear)
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from cipher.tasks.schema import Task, TaskIntent, TaskType, TaskStatus
from cipher.tasks.store import TaskStore
from cipher.tasks.analyzer import TaskAnalyzer
from cipher.tasks.sources.base import RawTicket
from cipher.tasks.sources.manual import ManualSource
from cipher.tasks.sources.github import GitHubIssueSource, _URL_PATTERN, _REF_PATTERN
from cipher.tasks.sources.linear import LinearSource, _ID_PATTERN, _URL_PATTERN as LINEAR_URL

from cipher.index.schema import Import, Symbol, FileIndex, RepoIndex, IndexStats
from cipher.graph.schema import GraphNode, GraphEdge, DependencyGraph


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_task(task_id="t001", status=TaskStatus.PENDING.value,
              task_type=TaskType.BUG.value) -> Task:
    return Task(
        task_id=task_id, type=task_type,
        title="Fix login bug", description="Login fails on timeout",
        repo="myrepo", client="myclient",
        status=status, created_at="2024-01-01T00:00:00+00:00",
        source="manual", source_ref="",
        target_files=[], context_pack_id="", intent_path="",
    )


def make_symbol(name: str, kind: str = "function") -> Symbol:
    return Symbol(name=name, kind=kind, line=1, parent=None, decorators=[])


def make_file(path: str, language: str = "python", symbols=None) -> FileIndex:
    return FileIndex(
        path=path, language=language,
        imports=[], symbols=symbols or [],
        parse_error=None, size_bytes=100, lines=10,
    )


def make_repo(*files: FileIndex) -> RepoIndex:
    return RepoIndex(
        repo_name="myrepo", repo_path="/repo",
        files=list(files),
        stats=IndexStats(0, 0, 0, 0, 0, {}, 0.0, ""),
    )


def make_graph(*edges, files=None) -> DependencyGraph:
    nodes = {}
    if files:
        nodes = {f.path: GraphNode(f.path, f.language, 0) for f in files}
    for f, t in edges:
        nodes.setdefault(f, GraphNode(f, "python", 0))
        nodes.setdefault(t, GraphNode(t, "python", 0))
    edge_objs = [GraphEdge(f, t, "import", []) for f, t in edges]
    return DependencyGraph("myrepo", "/repo", "", "0.4.0", nodes, edge_objs, {})


# ─── Schema serialization ─────────────────────────────────────────────────────

def test_task_roundtrip():
    t = make_task()
    t2 = Task.from_dict(t.to_dict())
    assert t2.task_id == t.task_id
    assert t2.type == t.type
    assert t2.status == t.status


def test_task_intent_roundtrip():
    intent = TaskIntent(
        task_id="t001", task_type="BUG", title="Fix auth",
        description="Auth fails", repo="myrepo",
        files_to_modify=["auth/login.py"],
        files_to_read=["auth/models.py"],
        rules_applied=["no direct DB calls"],
        constraints=["no breaking changes"],
        context_pack_path="/packs/t001/context_pack.md",
        generated_at="2024-01-01T00:00:00+00:00",
    )
    i2 = TaskIntent.from_dict(intent.to_dict())
    assert i2.task_id == intent.task_id
    assert i2.files_to_modify == intent.files_to_modify
    assert i2.constraints == intent.constraints


def test_task_type_values():
    assert TaskType.FEATURE.value == "FEATURE"
    assert TaskType.BUG.value == "BUG"
    assert TaskType.HOTFIX.value == "HOTFIX"
    assert TaskType.TASK.value == "TASK"


def test_task_status_values():
    assert TaskStatus.PENDING.value == "PENDING"
    assert TaskStatus.IN_PROGRESS.value == "IN_PROGRESS"
    assert TaskStatus.DONE.value == "DONE"
    assert TaskStatus.FAILED.value == "FAILED"


# ─── TaskStore ────────────────────────────────────────────────────────────────

def test_store_save_load(tmp_path):
    store = TaskStore(str(tmp_path))
    task = make_task()
    store.save_task(task)
    loaded = store.load_task("myclient", "myrepo", "t001")
    assert loaded is not None
    assert loaded.task_id == "t001"
    assert loaded.title == "Fix login bug"


def test_store_load_missing(tmp_path):
    store = TaskStore(str(tmp_path))
    assert store.load_task("c", "r", "nonexistent") is None


def test_store_update_status(tmp_path):
    store = TaskStore(str(tmp_path))
    task = make_task()
    store.save_task(task)
    store.update_status(task, TaskStatus.DONE.value)
    loaded = store.load_task("myclient", "myrepo", "t001")
    assert loaded.status == "DONE"


def test_store_list_tasks(tmp_path):
    store = TaskStore(str(tmp_path))
    store.save_task(make_task("t001", status="PENDING"))
    store.save_task(make_task("t002", status="DONE"))
    store.save_task(make_task("t003", status="PENDING"))

    all_tasks = store.list_tasks()
    assert len(all_tasks) == 3


def test_store_list_filter_status(tmp_path):
    store = TaskStore(str(tmp_path))
    store.save_task(make_task("t001", status="PENDING"))
    store.save_task(make_task("t002", status="DONE"))

    pending = store.list_tasks(status="PENDING")
    assert len(pending) == 1
    assert pending[0].task_id == "t001"


def test_store_list_empty(tmp_path):
    store = TaskStore(str(tmp_path))
    assert store.list_tasks() == []


def test_store_save_load_intent(tmp_path):
    store = TaskStore(str(tmp_path))
    intent = TaskIntent(
        task_id="t001", task_type="BUG", title="Fix",
        description="desc", repo="myrepo",
        files_to_modify=["a.py"], files_to_read=[],
        rules_applied=[], constraints=[],
        context_pack_path="", generated_at="",
    )
    store.save_intent(intent, "myclient", "myrepo")
    loaded = store.load_intent("myclient", "myrepo", "t001")
    assert loaded is not None
    assert loaded.files_to_modify == ["a.py"]


# ─── TaskAnalyzer ─────────────────────────────────────────────────────────────

def test_analyzer_detect_type_bug():
    files = [make_file("a.py")]
    analyzer = TaskAnalyzer(make_repo(*files), make_graph(files=files))
    assert analyzer.detect_type("fix login bug", "") == "BUG"


def test_analyzer_detect_type_hotfix():
    files = [make_file("a.py")]
    analyzer = TaskAnalyzer(make_repo(*files), make_graph(files=files))
    assert analyzer.detect_type("HOTFIX: production crash", "") == "HOTFIX"


def test_analyzer_detect_type_feature():
    files = [make_file("a.py")]
    analyzer = TaskAnalyzer(make_repo(*files), make_graph(files=files))
    assert analyzer.detect_type("add new user profile endpoint", "") == "FEATURE"


def test_analyzer_detect_type_default():
    files = [make_file("a.py")]
    analyzer = TaskAnalyzer(make_repo(*files), make_graph(files=files))
    assert analyzer.detect_type("update documentation", "") == "TASK"


def test_analyzer_detect_constraint_no_breaking():
    files = [make_file("a.py")]
    analyzer = TaskAnalyzer(make_repo(*files), make_graph(files=files))
    constraints = analyzer.detect_constraints("backward compat", "no breaking changes")
    assert "no breaking changes" in constraints


def test_analyzer_detect_no_constraints():
    files = [make_file("a.py")]
    analyzer = TaskAnalyzer(make_repo(*files), make_graph(files=files))
    constraints = analyzer.detect_constraints("fix auth bug", "timeout on login")
    assert constraints == []


def test_analyzer_find_candidate_files():
    files = [
        make_file("auth/login.py", symbols=[make_symbol("login")]),
        make_file("utils/helper.py", symbols=[make_symbol("help")]),
        make_file("db/models.py", symbols=[make_symbol("User")]),
    ]
    graph = make_graph(files=files)
    analyzer = TaskAnalyzer(make_repo(*files), graph)
    modify, read = analyzer.find_candidate_files("fix login auth", "")
    assert "auth/login.py" in modify


def test_analyzer_find_candidate_deps_in_read():
    # db/schema.py no tiene tokens relacionados con "login" → score=0 → entra via expansión
    login = make_file("auth/login.py", symbols=[make_symbol("login")])
    schema = make_file("db/schema.py")  # path no contiene "login" ni "auth"
    graph = make_graph(("auth/login.py", "db/schema.py"), files=[login, schema])
    analyzer = TaskAnalyzer(make_repo(login, schema), graph)
    modify, read = analyzer.find_candidate_files("fix login bug", "")
    assert "auth/login.py" in modify
    assert "db/schema.py" in read


def test_analyzer_build_intent():
    task = make_task(task_type=TaskType.BUG.value)
    files = [make_file("auth/login.py", symbols=[make_symbol("login")])]
    graph = make_graph(files=files)
    analyzer = TaskAnalyzer(make_repo(*files), graph)
    intent = analyzer.build_intent(task, context_pack_path="/packs/t001/context_pack.md")
    assert intent.task_id == "t001"
    assert intent.task_type == "BUG"
    assert intent.context_pack_path == "/packs/t001/context_pack.md"
    assert intent.generated_at  # not empty


# ─── ManualSource ─────────────────────────────────────────────────────────────

def test_manual_simple_description():
    src = ManualSource()
    ticket = src.fetch("fix login timeout bug")
    assert ticket.title == "fix login timeout bug"
    assert ticket.description == ""
    assert ticket.source == "manual"


def test_manual_title_colon_description():
    src = ManualSource()
    ticket = src.fetch("Fix auth: users get 500 on login")
    assert ticket.title == "Fix auth"
    assert ticket.description == "users get 500 on login"


def test_manual_source_ref_empty():
    src = ManualSource()
    ticket = src.fetch("any task")
    assert ticket.source_ref == ""
    assert ticket.labels == []


# ─── GitHubIssueSource ────────────────────────────────────────────────────────

def test_github_parse_url():
    src = GitHubIssueSource()
    owner, repo, num = src._parse_ref("https://github.com/myorg/myrepo/issues/42")
    assert owner == "myorg"
    assert repo == "myrepo"
    assert num == "42"


def test_github_parse_short_ref():
    src = GitHubIssueSource()
    owner, repo, num = src._parse_ref("myorg/myrepo#42")
    assert owner == "myorg"
    assert repo == "myrepo"
    assert num == "42"


def test_github_parse_slash_ref():
    src = GitHubIssueSource()
    owner, repo, num = src._parse_ref("myorg/myrepo/42")
    assert owner == "myorg"
    assert repo == "myrepo"
    assert num == "42"


def test_github_parse_invalid():
    src = GitHubIssueSource()
    with pytest.raises(ValueError, match="inválido"):
        src._parse_ref("not-a-valid-ref")


def test_github_fetch_mocked():
    src = GitHubIssueSource()
    mock_response = {
        "title": "Fix auth timeout",
        "body": "Users get 500 when session expires",
        "html_url": "https://github.com/org/repo/issues/1",
        "labels": [{"name": "bug"}, {"name": "auth"}],
        "state": "open",
    }
    with patch.object(src, "_request", return_value=mock_response):
        ticket = src.fetch("org/repo#1")
    assert ticket.title == "Fix auth timeout"
    assert ticket.source == "github"
    assert "bug" in ticket.labels
    assert ticket.source_ref == "https://github.com/org/repo/issues/1"


# ─── LinearSource ─────────────────────────────────────────────────────────────

def test_linear_parse_id():
    src = LinearSource()
    assert src._parse_ref("ENG-123") == "ENG-123"
    assert src._parse_ref("TEAM-999") == "TEAM-999"


def test_linear_parse_url():
    src = LinearSource()
    result = src._parse_ref("https://linear.app/myworkspace/issue/ENG-42/fix-auth")
    assert result == "ENG-42"


def test_linear_parse_invalid():
    src = LinearSource()
    with pytest.raises(ValueError, match="inválido"):
        src._parse_ref("not-a-linear-ref")


def test_linear_no_api_key():
    src = LinearSource()
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("LINEAR_API_KEY", None)
        with pytest.raises(ValueError, match="LINEAR_API_KEY"):
            src.fetch("ENG-123")


def test_linear_fetch_mocked():
    src = LinearSource()
    mock_response = {
        "data": {
            "issue": {
                "id": "abc",
                "identifier": "ENG-42",
                "title": "Fix payment flow",
                "description": "Payments fail on retry",
                "url": "https://linear.app/ws/issue/ENG-42",
                "state": {"name": "In Progress"},
                "labels": {"nodes": [{"name": "bug"}]},
                "priority": 1,
            }
        }
    }
    with patch.dict(os.environ, {"LINEAR_API_KEY": "test-key"}):
        with patch.object(src, "_request", return_value=mock_response):
            ticket = src.fetch("ENG-42")
    assert ticket.title == "Fix payment flow"
    assert ticket.source == "linear"
    assert "bug" in ticket.labels
