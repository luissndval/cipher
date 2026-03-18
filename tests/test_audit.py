"""
Tests — cipher Manifest & Audit System (Fase 5)
Cubre: schema, AuditWriter, AuditReader, pr_comment
"""

import json
import os
import pytest

from cipher.audit.schema import ContextManifest, AuditEntry, BRAIN_VERSION
from cipher.audit.writer import AuditWriter
from cipher.audit.reader import AuditReader
from cipher.audit.pr_comment import generate_pr_comment, _progress_bar
from cipher.pack.schema import PackManifest


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_pack_manifest(task_id="t001", provider="claude") -> PackManifest:
    return PackManifest(
        task_id=task_id,
        task_description="Fix login bug",
        repo_name="myrepo",
        repo_path="/repo",
        built_at="2024-01-01T00:00:00+00:00",
        brain_version="0.3.0",
        provider=provider,
        token_budget=60_000,
        tokens_used=5_000,
        files_included=[
            {"path": "auth/login.py", "role": "target", "tokens": 300, "language": "python"},
            {"path": "auth/models.py", "role": "dependency", "tokens": 100, "language": "python"},
        ],
        context_pack_hash="deadbeef" * 8,
    )


def make_manifest(manifest_id="m001", task_id="t001", result="pending") -> ContextManifest:
    return ContextManifest(
        manifest_id=manifest_id,
        task_id=task_id,
        session_id="",
        event="task_run",
        timestamp="2024-01-01T00:00:00+00:00",
        model="claude",
        brain_version=BRAIN_VERSION,
        repo="myrepo",
        client="myclient",
        files_used=[
            {"path": "auth/login.py", "role": "target", "tokens": 300},
            {"path": "auth/models.py", "role": "dependency", "tokens": 100},
        ],
        dependencies_included=["auth/models.py"],
        rules_applied=["no direct DB calls"],
        token_budget=60_000,
        tokens_used=5_000,
        context_pack_hash="deadbeef" * 8,
        pr_url="",
        result=result,
        manifest_path="",
    )


# ─── Schema ───────────────────────────────────────────────────────────────────

def test_context_manifest_roundtrip():
    m = make_manifest()
    m2 = ContextManifest.from_dict(m.to_dict())
    assert m2.manifest_id == m.manifest_id
    assert m2.files_used == m.files_used
    assert m2.dependencies_included == m.dependencies_included


def test_audit_entry_from_manifest():
    m = make_manifest()
    e = AuditEntry.from_manifest(m)
    assert e.entry_id == m.manifest_id
    assert e.task_id == m.task_id
    assert e.tokens_used == m.tokens_used
    assert e.files_count == 2


def test_audit_entry_roundtrip():
    m = make_manifest()
    e = AuditEntry.from_manifest(m)
    e2 = AuditEntry.from_dict(e.to_dict())
    assert e2.entry_id == e.entry_id
    assert e2.result == e.result


def test_manifest_files_count():
    m = make_manifest()
    assert m.files_count == 2


def test_manifest_budget_pct():
    m = make_manifest()
    assert m.budget_pct == 8   # 5000/60000 = 8%


def test_manifest_budget_pct_zero_budget():
    m = make_manifest()
    m.token_budget = 0
    assert m.budget_pct == 0


# ─── AuditWriter ──────────────────────────────────────────────────────────────

def test_writer_build_manifest_from_pack(tmp_path):
    writer = AuditWriter(str(tmp_path))
    pm = make_pack_manifest()
    manifest = writer.build_manifest(pm, event="task_run", task_id="t001")
    assert manifest.task_id == "t001"
    assert manifest.model == "claude"
    assert manifest.token_budget == 60_000
    assert manifest.tokens_used == 5_000
    assert manifest.context_pack_hash == pm.context_pack_hash
    assert len(manifest.manifest_id) == 36  # UUID


def test_writer_build_manifest_deps_extracted(tmp_path):
    writer = AuditWriter(str(tmp_path))
    pm = make_pack_manifest()
    manifest = writer.build_manifest(pm)
    assert "auth/models.py" in manifest.dependencies_included
    assert "auth/login.py" not in manifest.dependencies_included  # es target, no dep


def test_writer_save_manifest(tmp_path):
    writer = AuditWriter(str(tmp_path))
    pm = make_pack_manifest()
    manifest = writer.build_manifest(pm)
    path = writer.save_manifest(manifest, "myclient", "myrepo", "t001")
    assert os.path.exists(path)
    with open(path) as f:
        data = json.load(f)
    assert data["manifest_id"] == manifest.manifest_id
    assert data["client"] == "myclient"


def test_writer_save_manifest_path_structure(tmp_path):
    writer = AuditWriter(str(tmp_path))
    manifest = make_manifest()
    path = writer.save_manifest(manifest, "c1", "r1", "t1")
    # Debe estar en .cipher/sessions/c1/r1/t1/CONTEXT_MANIFEST.json
    assert ".cipher" in path
    assert "sessions" in path
    assert "c1" in path
    assert "t1" in path
    assert path.endswith("CONTEXT_MANIFEST.json")


def test_writer_append_entry(tmp_path):
    writer = AuditWriter(str(tmp_path))
    m1 = make_manifest("m001", "t001")
    m2 = make_manifest("m002", "t002")
    writer.append_entry(m1)
    writer.append_entry(m2)

    assert os.path.exists(writer.log_path)
    with open(writer.log_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    assert len(lines) == 2
    entries = [json.loads(l) for l in lines]
    ids = {e["entry_id"] for e in entries}
    assert "m001" in ids
    assert "m002" in ids


def test_writer_update_entry(tmp_path):
    writer = AuditWriter(str(tmp_path))
    m = make_manifest()
    writer.append_entry(m)
    writer.update_entry(m.manifest_id, result="done", pr_url="https://github.com/pr/1")

    with open(writer.log_path) as f:
        data = json.loads(f.readline())
    assert data["result"] == "done"
    assert data["pr_url"] == "https://github.com/pr/1"


def test_writer_update_manifest(tmp_path):
    writer = AuditWriter(str(tmp_path))
    manifest = make_manifest()
    path = writer.save_manifest(manifest, "c", "r", "t001")
    writer.update_manifest(manifest, result="done", pr_url="https://pr/1")

    with open(path) as f:
        data = json.load(f)
    assert data["result"] == "done"
    assert data["pr_url"] == "https://pr/1"


def test_writer_update_entry_missing_id(tmp_path):
    writer = AuditWriter(str(tmp_path))
    m = make_manifest()
    writer.append_entry(m)
    # Actualizar ID inexistente no debe fallar
    writer.update_entry("nonexistent", result="done")
    # El entry original permanece sin cambios
    with open(writer.log_path) as f:
        data = json.loads(f.readline())
    assert data["result"] == "pending"


# ─── AuditReader ──────────────────────────────────────────────────────────────

def _setup_log(tmp_path, *manifests):
    writer = AuditWriter(str(tmp_path))
    for m in manifests:
        writer.append_entry(m)
    return AuditReader(str(tmp_path))


def test_reader_empty_log(tmp_path):
    reader = AuditReader(str(tmp_path))
    assert reader.entries() == []


def test_reader_all_entries(tmp_path):
    reader = _setup_log(
        tmp_path,
        make_manifest("m1", "t1"),
        make_manifest("m2", "t2"),
    )
    entries = reader.entries()
    assert len(entries) == 2


def test_reader_filter_task_id(tmp_path):
    reader = _setup_log(
        tmp_path,
        make_manifest("m1", "t1"),
        make_manifest("m2", "t2"),
    )
    entries = reader.entries(task_id="t1")
    assert len(entries) == 1
    assert entries[0].task_id == "t1"


def test_reader_filter_repo(tmp_path):
    writer = AuditWriter(str(tmp_path))
    m1 = make_manifest("m1", "t1"); m1.repo = "repo-a"
    m2 = make_manifest("m2", "t2"); m2.repo = "repo-b"
    writer.append_entry(m1)
    writer.append_entry(m2)
    reader = AuditReader(str(tmp_path))

    entries = reader.entries(repo="repo-a")
    assert len(entries) == 1
    assert entries[0].repo == "repo-a"


def test_reader_filter_result(tmp_path):
    reader = _setup_log(
        tmp_path,
        make_manifest("m1", "t1", result="done"),
        make_manifest("m2", "t2", result="pending"),
        make_manifest("m3", "t3", result="failed"),
    )
    done = reader.entries(result="done")
    assert len(done) == 1
    assert done[0].result == "done"


def test_reader_filter_since(tmp_path):
    writer = AuditWriter(str(tmp_path))
    m1 = make_manifest("m1", "t1"); m1.timestamp = "2023-06-01T00:00:00+00:00"
    m2 = make_manifest("m2", "t2"); m2.timestamp = "2024-03-01T00:00:00+00:00"
    writer.append_entry(m1)
    writer.append_entry(m2)
    reader = AuditReader(str(tmp_path))

    entries = reader.entries(since="2024")
    assert len(entries) == 1
    assert entries[0].task_id == "t2"


def test_reader_load_manifest(tmp_path):
    writer = AuditWriter(str(tmp_path))
    m = make_manifest()
    path = writer.save_manifest(m, "c", "r", "t001")
    reader = AuditReader(str(tmp_path))
    loaded = reader.load_manifest(path)
    assert loaded is not None
    assert loaded.manifest_id == m.manifest_id


def test_reader_load_manifest_missing(tmp_path):
    reader = AuditReader(str(tmp_path))
    assert reader.load_manifest("/nonexistent/path.json") is None


def test_reader_find_manifest(tmp_path):
    writer = AuditWriter(str(tmp_path))
    m = make_manifest("m001", "t001")
    path = writer.save_manifest(m, "c", "r", "t001")
    m.manifest_path = path
    writer.append_entry(m)
    reader = AuditReader(str(tmp_path))
    found = reader.find_manifest("t001")
    assert found is not None
    assert found.task_id == "t001"


def test_reader_stats(tmp_path):
    writer = AuditWriter(str(tmp_path))
    m1 = make_manifest("m1", "t1", result="done"); m1.repo = "repo-a"
    m2 = make_manifest("m2", "t2", result="failed"); m2.repo = "repo-a"
    m3 = make_manifest("m3", "t3", result="done"); m3.repo = "repo-b"
    for m in (m1, m2, m3):
        writer.append_entry(m)
    reader = AuditReader(str(tmp_path))
    s = reader.stats()
    assert s["total"] == 3
    assert s["total_tokens_used"] == 3 * 5_000
    assert s["by_result"]["done"] == 2
    assert s["by_result"]["failed"] == 1
    assert s["by_repo"]["repo-a"] == 2


def test_reader_stats_empty(tmp_path):
    reader = AuditReader(str(tmp_path))
    s = reader.stats()
    assert s["total"] == 0


# ─── PR Comment ───────────────────────────────────────────────────────────────

def test_pr_comment_contains_task_id():
    m = make_manifest()
    comment = generate_pr_comment(m)
    assert "t001" in comment  # task_id, no manifest_id


def test_pr_comment_contains_model():
    m = make_manifest()
    comment = generate_pr_comment(m)
    assert "claude" in comment


def test_pr_comment_contains_files():
    m = make_manifest()
    comment = generate_pr_comment(m)
    assert "auth/login.py" in comment
    assert "auth/models.py" in comment


def test_pr_comment_contains_hash():
    m = make_manifest()
    comment = generate_pr_comment(m)
    assert "deadbeef" in comment


def test_pr_comment_no_hash():
    m = make_manifest()
    comment = generate_pr_comment(m, include_hash=False)
    assert "deadbeef" not in comment


def test_pr_comment_contains_rules():
    m = make_manifest()
    comment = generate_pr_comment(m)
    assert "no direct DB calls" in comment


def test_pr_comment_contains_deps():
    m = make_manifest()
    comment = generate_pr_comment(m)
    assert "models.py" in comment


def test_progress_bar_full():
    assert _progress_bar(100) == "█" * 10


def test_progress_bar_empty():
    assert _progress_bar(0) == "░" * 10


def test_progress_bar_half():
    bar = _progress_bar(50)
    assert "█" in bar
    assert "░" in bar
    assert len(bar) == 10
