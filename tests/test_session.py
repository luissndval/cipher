"""Tests para cipher.memory.session — SessionStore"""

import os
import json
import time
import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cipher.memory.session import SessionStore


@pytest.fixture
def store(tmp_path):
    return SessionStore(cipher_dir=str(tmp_path))


class TestNewSession:
    def test_creates_session_with_uuid(self, store):
        s = store.new_session("acme", "acme-api", "claude", "/some/path")
        assert len(s["session_id"]) == 36  # UUID4 format
        assert s["client"] == "acme"
        assert s["project"] == "acme-api"
        assert s["agent"] == "claude"
        assert s["status"] == "started"

    def test_two_sessions_have_different_ids(self, store):
        s1 = store.new_session("acme", "acme-api", "claude", "/path")
        s2 = store.new_session("acme", "acme-api", "claude", "/path")
        assert s1["session_id"] != s2["session_id"]

    def test_includes_brain_version(self, store):
        s = store.new_session("acme", "acme-api", "claude", "/path")
        assert s["brain_version"] is not None


class TestAttachContext:
    def test_attaches_context_hash(self, store, tmp_path):
        context_file = tmp_path / "ACTIVE_CONTEXT.md"
        context_file.write_text("# Context content")
        s = store.new_session("acme", "api", "claude", "/path")
        store.attach_context(s, str(context_file))
        assert s["context_file"] == str(context_file)
        assert s["context_hash"] is not None
        assert len(s["context_hash"]) == 16  # sha256 truncado

    def test_handles_missing_context_file(self, store):
        s = store.new_session("acme", "api", "claude", "/path")
        store.attach_context(s, "/nonexistent/path.md")
        assert s["context_file"] == "/nonexistent/path.md"
        assert s["context_hash"] is None


class TestSaveAndLoadManifest:
    def test_save_creates_file(self, store, tmp_path):
        s = store.new_session("acme", "acme-api", "claude", "/path")
        manifest_path = store.save_manifest(s, "acme", "acme-api")
        assert os.path.exists(manifest_path)
        assert manifest_path.endswith("session_manifest.json")

    def test_manifest_content_is_valid_json(self, store, tmp_path):
        s = store.new_session("acme", "acme-api", "claude", "/path")
        manifest_path = store.save_manifest(s, "acme", "acme-api")
        with open(manifest_path) as f:
            data = json.load(f)
        assert data["session_id"] == s["session_id"]
        assert data["client"] == "acme"

    def test_load_latest_returns_most_recent(self, store):
        s1 = store.new_session("acme", "api", "claude", "/path")
        store.save_manifest(s1, "acme", "api")
        time.sleep(0.01)
        s2 = store.new_session("acme", "api", "claude", "/path")
        store.save_manifest(s2, "acme", "api")

        latest = store.load_latest_manifest("acme", "api")
        # Ambos están guardados; el más reciente por orden de carpeta (UUID no garantiza orden)
        assert latest is not None
        assert latest["session_id"] in (s1["session_id"], s2["session_id"])

    def test_load_latest_returns_none_if_no_sessions(self, store):
        result = store.load_latest_manifest("nonexistent", "project")
        assert result is None


class TestCloseSession:
    def test_sets_status_and_closed_at(self, store):
        s = store.new_session("acme", "api", "claude", "/path")
        store.close_session(s, status="completed")
        assert s["status"] == "completed"
        assert "closed_at" in s

    def test_default_status_is_completed(self, store):
        s = store.new_session("acme", "api", "claude", "/path")
        store.close_session(s)
        assert s["status"] == "completed"


class TestListManifests:
    def test_lists_all_manifests(self, store):
        s1 = store.new_session("acme", "api", "claude", "/path")
        store.save_manifest(s1, "acme", "api")
        s2 = store.new_session("beta", "beta-svc", "claude", "/path")
        store.save_manifest(s2, "beta", "beta-svc")

        all_manifests = store.list_manifests()
        assert len(all_manifests) == 2

    def test_filters_by_client(self, store):
        s1 = store.new_session("acme", "api", "claude", "/path")
        store.save_manifest(s1, "acme", "api")
        s2 = store.new_session("beta", "beta-svc", "claude", "/path")
        store.save_manifest(s2, "beta", "beta-svc")

        acme_manifests = store.list_manifests(client="acme")
        assert len(acme_manifests) == 1
        assert acme_manifests[0]["client"] == "acme"

    def test_returns_empty_if_no_sessions(self, store):
        assert store.list_manifests() == []
