"""
cipher core — Config
Carga y guarda configuración de providers desde config.local.json y env vars.
"""

import os
import json
from pathlib import Path


def find_local_config() -> Path:
    """Resuelve config.local.json desde CIPHER_PATH o la ruta del paquete."""
    cipher_path = os.environ.get("CIPHER_PATH")
    if cipher_path:
        return Path(cipher_path) / ".cipher" / "config.local.json"
    # Fallback: dos niveles arriba de cipher/core/
    return Path(__file__).parent.parent.parent / ".cipher" / "config.local.json"


def load_config() -> dict:
    """
    Carga configuración en orden de prioridad:
    1. Variables de entorno
    2. config.local.json

    Estructura esperada de config.local.json:
    {
      "anthropic": { "api_key": "...", "model": "claude-sonnet-4-6" },
      "google":    { "api_key": "...", "model": "gemini-2.5-flash" }
    }
    """
    cfg = {
        "anthropic": {"api_key": "", "auth": "none", "model": "claude-sonnet-4-6"},
        "google":    {"api_key": "", "auth": "none", "model": "gemini-2.5-flash"},
    }

    local_config = find_local_config()
    if local_config.exists():
        with open(local_config) as f:
            local = json.load(f)
        for provider, values in local.items():
            if provider in cfg and isinstance(values, dict):
                for k, v in values.items():
                    if v:
                        cfg[provider][k] = v

    env_map = {
        "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH", "ANTHROPIC_MODEL"),
        "google":    ("GOOGLE_API_KEY",    "GOOGLE_AUTH",    "GOOGLE_MODEL"),
    }
    for provider, (key_var, auth_var, model_var) in env_map.items():
        if os.environ.get(key_var):
            cfg[provider]["api_key"] = os.environ[key_var]
        if os.environ.get(auth_var):
            cfg[provider]["auth"] = os.environ[auth_var]
        if os.environ.get(model_var):
            cfg[provider]["model"] = os.environ[model_var]

    return cfg


def save_provider_config(provider: str, updates: dict):
    """Guarda o actualiza configuración de un provider en config.local.json."""
    local_config = find_local_config()
    local_config.parent.mkdir(parents=True, exist_ok=True)

    cfg = {}
    if local_config.exists():
        with open(local_config) as f:
            cfg = json.load(f)

    if provider not in cfg:
        cfg[provider] = {}
    cfg[provider].update(updates)

    with open(local_config, "w") as f:
        json.dump(cfg, f, indent=2)
