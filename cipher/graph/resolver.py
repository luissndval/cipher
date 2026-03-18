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

    def resolve(self, imp: Import, from_file: str, language: str) -> str | None:
        """
        Intenta resolver un import a un rel_path en el repo.
        Retorna el rel_path si lo encuentra, None si es externo/stdlib.
        """
        if imp.is_relative:
            if language == "python":
                return self._python_relative(imp, from_file)
            if language in ("typescript", "javascript"):
                return self._ts_relative(imp, from_file)
            return None
        else:
            if language == "python":
                return self._python_absolute(imp)
            # TS/Go non-relative → siempre externo en Fase 2
            return None

    # ─── Python ───────────────────────────────────────────────────────────────

    def _python_relative(self, imp: Import, from_file: str) -> str | None:
        """
        Resuelve imports relativos Python.
        .utils        → mismo paquete, archivo utils.py
        ..models      → paquete padre, archivo models.py
        ...pkg.sub    → dos niveles arriba, pkg/sub.py
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
                return None
            parts = parts[:-up]

        base_dir = "/".join(parts)

        if rest:
            module_path = rest.replace(".", "/")
            prefix = f"{base_dir}/" if base_dir else ""
            candidates = [
                f"{prefix}{module_path}.py",
                f"{prefix}{module_path}/__init__.py",
            ]
        else:
            # from . import something → __init__.py del mismo paquete
            prefix = f"{base_dir}/" if base_dir else ""
            candidates = [f"{prefix}__init__.py"]

        return next((c for c in candidates if c in self.known_files), None)

    def _python_absolute(self, imp: Import) -> str | None:
        """
        Intenta encontrar un módulo Python absoluto en el repo.
        Solo funciona si el módulo es parte del proyecto (no stdlib/third-party).
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
        return next((c for c in candidates if c in self.known_files), None)

    # ─── TypeScript / JavaScript ───────────────────────────────────────────────

    def _ts_relative(self, imp: Import, from_file: str) -> str | None:
        """
        Resuelve imports relativos TypeScript/JS.
        Intenta extensiones TS/JS y archivos index.
        """
        file_dir = os.path.dirname(from_file).replace("\\", "/")
        # Combinar dir del archivo con el path del import y normalizar
        raw = os.path.normpath(os.path.join(file_dir, imp.module)).replace("\\", "/")

        # 1. El import ya tiene extensión
        if raw in self.known_files:
            return raw

        # 2. Probar extensiones
        for ext in self.TS_EXTENSIONS:
            if (raw + ext) in self.known_files:
                return raw + ext

        # 3. Probar como directorio con index file
        for index_name in self.TS_INDEX_NAMES:
            candidate = f"{raw}/{index_name}"
            if candidate in self.known_files:
                return candidate

        return None
