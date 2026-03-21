"""Tests para cipher.core.config"""

import os
import json
import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cipher.core.config import load_config, save_provider_config


class TestLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CIPHER_PATH", str(tmp_path))
        # No existe config.local.json → retorna defaults
        cfg = load_config()
        assert cfg["anthropic"]["model"] == "claude-sonnet-4-6"
        assert cfg["google"]["model"] == "gemini-2.5-flash"
        assert cfg["anthropic"]["api_key"] == ""

    def test_loads_from_local_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CIPHER_PATH", str(tmp_path))
        cipher_dir = tmp_path / ".cipher"
        cipher_dir.mkdir()
        (cipher_dir / "config.local.json").write_text(json.dumps({
            "anthropic": {"api_key": "sk-test-123", "model": "claude-opus-4-6"},
        }))
        cfg = load_config()
        assert cfg["anthropic"]["api_key"] == "sk-test-123"
        assert cfg["anthropic"]["model"] == "claude-opus-4-6"

    def test_env_vars_override_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CIPHER_PATH", str(tmp_path))
        cipher_dir = tmp_path / ".cipher"
        cipher_dir.mkdir()
        (cipher_dir / "config.local.json").write_text(json.dumps({
            "anthropic": {"api_key": "sk-from-file"},
        }))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
        cfg = load_config()
        assert cfg["anthropic"]["api_key"] == "sk-from-env"

    def test_ignores_empty_values_in_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CIPHER_PATH", str(tmp_path))
        cipher_dir = tmp_path / ".cipher"
        cipher_dir.mkdir()
        (cipher_dir / "config.local.json").write_text(json.dumps({
            "anthropic": {"api_key": ""},
        }))
        cfg = load_config()
        assert cfg["anthropic"]["api_key"] == ""  # default se mantiene vacío


class TestSaveProviderConfig:
    def test_creates_file_if_not_exists(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CIPHER_PATH", str(tmp_path))
        save_provider_config("anthropic", {"api_key": "sk-new"})
        config_file = tmp_path / ".cipher" / "config.local.json"
        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["anthropic"]["api_key"] == "sk-new"

    def test_merges_with_existing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CIPHER_PATH", str(tmp_path))
        cipher_dir = tmp_path / ".cipher"
        cipher_dir.mkdir()
        (cipher_dir / "config.local.json").write_text(json.dumps({
            "google": {"api_key": "goog-key"},
        }))
        save_provider_config("anthropic", {"api_key": "sk-new"})
        data = json.loads((cipher_dir / "config.local.json").read_text())
        assert data["google"]["api_key"] == "goog-key"
        assert data["anthropic"]["api_key"] == "sk-new"
