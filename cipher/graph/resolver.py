"""
cipher graph — ImportResolver
Resuelve imports a rutas de archivos dentro del repo.
Determinístico: solo usa el índice de archivos, sin LLM.

Soporta:
  Python : imports relativos (.utils, ..models) + absolutos (mypackage.models)
  TS/JS  : imports relativos (./utils, ../models) con resolución de extensiones
  Go     : todos los imports son absolutos (módulos externos o stdlib → None)
"""

import os
from cipher.index.schema import Import


class ImportResolver:
    TS_EXTENSIONS  = (".ts", ".tsx", ".js", ".jsx")
    TS_INDEX_NAMES = ("index.ts", "index.tsx", "index.js", "index.jsx")

    def __init__(self, known_files: set):
        """
        known_files: conjunto de rel_paths (forward slashes) del índice del repo.
        """
        self.known_files = known_files

    def resolve(self, imp: Import, from_file: str, language: str) -> list:
        """
        Intenta resolver un import a rel_paths en el repo.
        Retorna lista de rel_paths encontrados (puede ser vacía).
        """
        if imp.is_relative:
            if language == "python":
                return self._python_relative(imp, from_file)
            if language in ("typescript", "javascript"):
                return self._ts_relative(imp, from_file)
            return []
        else:
            if language == "python":
                return self._python_absolute(imp)
            # TS/Go non-relative → siempre externo en Fase 2
            return []

    # ─── Python ───────────────────────────────────────────────────────────────

    def _python_relative(self, imp: Import, from_file: str) -> list:
        """
        Resuelve imports relativos Python.
        .utils        → mismo paquete, archivo utils.py
        ..models      → paquete padre, archivo models.py
        ...pkg.sub    → dos niveles arriba, pkg/sub.py
        from . import a, b → prueba a.py y b.py en el mismo paquete
        """
        module = imp.module   # ej: ".utils", "..models", ".."
        level = len(module) - len(module.lstrip("."))
        rest = module[level:]  # ej: "utils", "models", "pkg.sub", ""

        # Directorio base del archivo actual
        file_dir = os.path.dirname(from_file).replace("\\", "/")
        parts = file_dir.split("/") if file_dir else []

        # Subir (level - 1) directorios
        up = level - 1
        if up > 0:
            if up > len(parts):
                return []
            parts = parts[:-up]

        base_dir = "/".join(parts)
        prefix = f"{base_dir}/" if base_dir else ""

        if rest:
            module_path = rest.replace(".", "/")
            candidates = [
                f"{prefix}{module_path}.py",
                f"{prefix}{module_path}/__init__.py",
            ]
        else:
            # from . import a, b → __init__.py + cada nombre como posible submódulo
            candidates = [f"{prefix}__init__.py"]
            for name in (imp.names or []):
                candidates += [
                    f"{prefix}{name}.py",
                    f"{prefix}{name}/__init__.py",
                ]

        return [c for c in candidates if c in self.known_files]

    def _python_absolute(self, imp: Import) -> list:
        """
        Intenta encontrar módulos Python absolutos en el repo.
        Además del módulo principal, prueba cada nombre importado como submódulo.
        Ej: from app.api.v1 import menu → también prueba app/api/v1/menu.py
        """
        module_path = imp.module.replace(".", "/")
        candidates = [
            f"{module_path}.py",
            f"{module_path}/__init__.py",
        ]
        # Probar desde directorios raíz comunes
        for prefix in ("src", "app", "lib", "core"):
            candidates += [
                f"{prefix}/{module_path}.py",
                f"{prefix}/{module_path}/__init__.py",
            ]

        # Cada nombre importado puede ser un submódulo, no solo un símbolo
        for name in (imp.names or []):
            candidates += [
                f"{module_path}/{name}.py",
                f"{module_path}/{name}/__init__.py",
            ]
            for prefix in ("src", "app", "lib", "core"):
                candidates += [
                    f"{prefix}/{module_path}/{name}.py",
                    f"{prefix}/{module_path}/{name}/__init__.py",
                ]

        return [c for c in candidates if c in self.known_files]

    # ─── TypeScript / JavaScript ───────────────────────────────────────────────

    def _ts_relative(self, imp: Import, from_file: str) -> list:
        """
        Resuelve imports relativos TypeScript/JS.
        Intenta extensiones TS/JS y archivos index.
        """
        file_dir = os.path.dirname(from_file).replace("\\", "/")
        # Combinar dir del archivo con el path del import y normalizar
        raw = os.path.normpath(os.path.join(file_dir, imp.module)).replace("\\", "/")

        # 1. El import ya tiene extensión
        if raw in self.known_files:
            return [raw]

        # 2. Probar extensiones
        for ext in self.TS_EXTENSIONS:
            if (raw + ext) in self.known_files:
                return [raw + ext]

        # 3. Probar como directorio con index file
        for index_name in self.TS_INDEX_NAMES:
            candidate = f"{raw}/{index_name}"
            if candidate in self.known_files:
                return [candidate]

        return []
