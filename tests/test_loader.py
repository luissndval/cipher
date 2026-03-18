"""Tests para cipher.core.loader — ContextLoader"""

import os
import json
import tempfile
import pytest

# Agregar el root del proyecto al path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cipher.core.loader import ContextLoader


@pytest.fixture
def cipher_dir(tmp_path):
    """Crea una estructura mínima de cipher en un directorio temporal."""
    cipher_data = tmp_path / ".cipher"
    cipher_data.mkdir()

    config = {
        "version": "1.0",
        "clients": {
            "acme": {
                "repos": {
                    "acme-api": {
                        "name": "acme-api",
                        "path": str(tmp_path / "acme-api"),
                        "owner": "",
                        "depends_on": [],
                        "consumed_by": [],
                    },
                    "acme-frontend": {
                        "name": "acme-frontend",
                        "path": str(tmp_path / "acme-frontend"),
                        "owner": "",
                        "depends_on": [],
                        "consumed_by": [],
                    },
                }
            }
        },
    }
    (cipher_data / "config.json").write_text(json.dumps(config, indent=2))
    return str(tmp_path)


class TestContextLoaderInit:
    def test_loads_config(self, cipher_dir):
        loader = ContextLoader(cipher_dir=cipher_dir)
        assert loader.config["version"] == "1.0"
        assert "acme" in loader.config["clients"]

    def test_raises_if_config_missing(self, tmp_path):
        (tmp_path / ".cipher").mkdir()
        with pytest.raises(FileNotFoundError, match="config.json"):
            ContextLoader(cipher_dir=str(tmp_path))

    def test_raises_if_cipher_dir_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CIPHER_PATH", "")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CIPHER_PATH", raising=False)
        with pytest.raises(FileNotFoundError, match="No se encontró cipher"):
            ContextLoader()


class TestResolveProject:
    def test_resolves_by_repo_name(self, cipher_dir, monkeypatch):
        loader = ContextLoader(cipher_dir=cipher_dir)
        loader.repo_name = "acme-api"
        client, project = loader.resolve_project()
        assert client == "acme"
        assert project == "acme-api"

    def test_returns_none_for_unknown_repo(self, cipher_dir):
        loader = ContextLoader(cipher_dir=cipher_dir)
        loader.repo_name = "unknown-repo"
        client, project = loader.resolve_project()
        assert client is None
        assert project is None

    def test_ignores_malformed_client_entries(self, tmp_path):
        cipher_data = tmp_path / ".cipher"
        cipher_data.mkdir()
        config = {
            "version": "1.0",
            "clients": {
                "legacy": "/old/path/format",   # formato viejo (string)
                "acme": {
                    "repos": {
                        "acme-api": {"name": "acme-api", "path": "/some/path",
                                     "owner": "", "depends_on": [], "consumed_by": []}
                    }
                },
            },
        }
        (cipher_data / "config.json").write_text(json.dumps(config))
        loader = ContextLoader(cipher_dir=str(tmp_path))
        loader.repo_name = "acme-api"
        client, project = loader.resolve_project()
        assert client == "acme"
        assert project == "acme-api"

    def test_sets_client_and_project_on_loader(self, cipher_dir):
        loader = ContextLoader(cipher_dir=cipher_dir)
        loader.repo_name = "acme-frontend"
        loader.resolve_project()
        assert loader.client == "acme"
        assert loader.project == "acme-frontend"


class TestSessionDir:
    def test_session_dir_path(self, cipher_dir):
        loader = ContextLoader(cipher_dir=cipher_dir)
        path = loader.session_dir("acme", "acme-api")
        assert path == os.path.join(cipher_dir, ".cipher", "sessions", "acme", "acme-api")


class TestAssembleContext:
    def test_includes_draft_marker_for_project_layer(self, cipher_dir, tmp_path):
        # Crear archivos de proyecto
        project_dir = tmp_path / "clients" / "acme" / "acme-api"
        project_dir.mkdir(parents=True)
        (project_dir / "ARCHITECTURE.md").write_text("# Arch content")

        loader = ContextLoader(cipher_dir=cipher_dir)
        loader.repo_name = "acme-api"
        context = loader.assemble_context("acme", "acme-api", mode="full")
        assert "[DRAFT" in context

    def test_context_has_header_comment(self, cipher_dir):
        loader = ContextLoader(cipher_dir=cipher_dir)
        context = loader.assemble_context("acme", "acme-api", mode="summary")
        assert "GENERADO POR cipher" in context
