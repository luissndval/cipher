"""
cipher interactive — ContextSearcher
Busca archivos, carpetas y símbolos en el índice del repo.

Soporta búsqueda por:
  - nombre de archivo (basename)
  - path completo (substring)
  - nombre de símbolo (clase, función, método)
  - extensión / lenguaje
"""

import os
from dataclasses import dataclass


@dataclass
class SearchResult:
    path: str           # rel_path del archivo
    language: str
    match_type: str     # "path" | "symbol" | "basename"
    matched_on: str     # qué parte hizo match (para mostrar)
    score: float        # mayor = más relevante


class ContextSearcher:
    def __init__(self, repo_index, graph=None):
        self.repo_index = repo_index
        self.graph = graph
        # Índice de símbolos: nombre_lower → [(path, symbol)]
        self._symbol_index: dict = {}
        self._build_symbol_index()

    def _build_symbol_index(self):
        for file_index in self.repo_index.files:
            for sym in file_index.symbols:
                key = sym.name.lower()
                if key not in self._symbol_index:
                    self._symbol_index[key] = []
                self._symbol_index[key].append((file_index.path, sym.name, sym.kind))

    def search(self, query: str, limit: int = 15) -> list:
        """
        Busca archivos/símbolos que coincidan con query.
        Retorna list[SearchResult] ordenado por score desc.
        """
        if not query:
            return []
        q = query.lower().strip()
        seen: dict[str, SearchResult] = {}

        for file_index in self.repo_index.files:
            path = file_index.path
            path_lower = path.lower()
            basename = os.path.basename(path).lower()
            basename_no_ext = os.path.splitext(basename)[0]
            score = 0.0
            match_type = None
            matched_on = None

            # 1. Match exacto en basename (sin extensión)
            if q == basename_no_ext:
                score = 10.0; match_type = "basename"; matched_on = basename

            # 2. Match exacto en basename completo
            elif q == basename:
                score = 9.0; match_type = "basename"; matched_on = basename

            # 3. Basename empieza con query
            elif basename_no_ext.startswith(q):
                score = 7.0; match_type = "basename"; matched_on = basename

            # 4. Substring en basename
            elif q in basename:
                score = 5.0; match_type = "basename"; matched_on = basename

            # 5. Substring en path completo
            elif q in path_lower:
                # Más relevante si está cerca del final del path
                depth_bonus = path_lower.count("/")
                score = 3.0 + (path_lower.index(q) / max(len(path_lower), 1)) * -1
                match_type = "path"; matched_on = path

            if score > 0:
                seen[path] = SearchResult(
                    path=path, language=file_index.language,
                    match_type=match_type, matched_on=matched_on, score=score,
                )

        # 6. Buscar en símbolos
        for sym_key, entries in self._symbol_index.items():
            if q in sym_key:
                sym_score = 8.0 if sym_key == q else 4.0
                for path, sym_name, sym_kind in entries:
                    if path not in seen or seen[path].score < sym_score:
                        # Encontrar language del archivo
                        lang = next(
                            (f.language for f in self.repo_index.files if f.path == path),
                            "unknown",
                        )
                        seen[path] = SearchResult(
                            path=path, language=lang,
                            match_type="symbol",
                            matched_on=f"{sym_kind} {sym_name}",
                            score=sym_score,
                        )

        results = sorted(seen.values(), key=lambda r: r.score, reverse=True)
        return results[:limit]

    def search_multi(self, queries: list, limit: int = 15) -> list:
        """Busca múltiples queries y unifica resultados."""
        seen: dict[str, SearchResult] = {}
        for q in queries:
            for r in self.search(q, limit=limit):
                if r.path not in seen or seen[r.path].score < r.score:
                    seen[r.path] = r
        return sorted(seen.values(), key=lambda r: r.score, reverse=True)[:limit]
