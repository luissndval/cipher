"""
cipher index — Parser Registry
Mapea extensiones de archivo al parser correspondiente.
Para agregar soporte a un nuevo lenguaje:
  1. Crear una clase en parsers/ que extienda LanguageParser
  2. Agregarla a la lista en _build_registry()
"""

from cipher.index.parsers.python import PythonParser
from cipher.index.parsers.typescript import TypeScriptParser
from cipher.index.parsers.go import GoParser
from cipher.index.parsers.base import LanguageParser

_REGISTRY: dict[str, LanguageParser] = {}


def _build_registry():
    for parser in [PythonParser(), TypeScriptParser(), GoParser()]:
        for ext in parser.extensions:
            _REGISTRY[ext.lower()] = parser


_build_registry()


def get_parser(ext: str) -> LanguageParser | None:
    """Retorna el parser para una extensión, o None si no está soportada."""
    return _REGISTRY.get(ext.lower())


def supported_extensions() -> set:
    return set(_REGISTRY.keys())


def supported_languages() -> set:
    return {p.language for p in _REGISTRY.values()}
