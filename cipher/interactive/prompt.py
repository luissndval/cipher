"""
cipher interactive — InteractiveSession
Modo interactivo para cipher impact.

Flujo:
  1. Input libre con soporte para @menciones
  2. Al detectar @token, busca archivos/símbolos en el índice
  3. Selección numerada (simple o múltiple: 1,3,5 o 1-4)
  4. Iteración hasta confirmar
  5. Resumen del contexto → ejecución del análisis de impacto

Triggers:
  @     buscar archivo/símbolo
  /cls  limpiar contexto seleccionado
  /list listar archivos seleccionados
  Enter confirmar y ejecutar
"""

import os
import re

from cipher.interactive.searcher import ContextSearcher, SearchResult
from cipher.graph.schema import DependencyGraph
from cipher.index.schema import RepoIndex

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.shortcuts.prompt import CompleteStyle
    from prompt_toolkit.styles import Style
    from cipher.interactive.completer import AtMentionCompleter
    _PT = True
except ImportError:
    _PT = False

_PT_STYLE = None
if _PT:
    _PT_STYLE = Style.from_dict({
        "completion-menu.completion":         "bg:#1e3a5f #aaccff",
        "completion-menu.completion.current": "bg:#2255aa #ffffff bold",
        "completion-menu.meta.completion":    "bg:#142840 #667799",
        "completion-menu.meta.completion.current": "bg:#1a3d7a #99bbdd",
    })

GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BLUE   = '\033[0;34m'
CYAN   = '\033[0;36m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
NC     = '\033[0m'

_AT_PATTERN = re.compile(r'@([^\s@,;]+)')


class InteractiveSession:
    def __init__(
        self,
        repo_index: RepoIndex,
        graph: DependencyGraph,
        repo_name: str,
        max_depth: int = 10,
    ):
        self.repo_index = repo_index
        self.graph = graph
        self.repo_name = repo_name
        self.max_depth = max_depth
        self.searcher = ContextSearcher(repo_index, graph)
        self.selected: list[str] = []   # rel_paths seleccionados
        self.intention: str = ""

    def run(self) -> bool:
        """
        Ejecuta la sesión interactiva.
        Retorna True si se ejecutó el análisis, False si el usuario canceló.
        """
        self._header()

        # PromptSession con autocompletado de @menciones
        session = None
        if _PT:
            session = PromptSession(
                completer=AtMentionCompleter(self.searcher),
                complete_style=CompleteStyle.MULTI_COLUMN,
                style=_PT_STYLE,
                complete_while_typing=True,
            )

        while True:
            try:
                if session:
                    raw = session.prompt("\n> ").strip()
                else:
                    raw = input(f"\n{CYAN}>{NC} ").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n\n  {YELLOW}Cancelado.{NC}\n")
                return False

            if not raw:
                if self.selected:
                    break          # Enter con contexto → ejecutar
                print(f"  {DIM}Escribí algo o usá @nombre para buscar archivos.{NC}")
                continue

            # Comandos especiales
            if raw == "/cls":
                self.selected = []
                self.intention = ""
                print(f"  {YELLOW}Contexto limpiado.{NC}")
                continue
            if raw == "/list":
                self._show_selected()
                continue

            # Procesar @menciones en el input
            try:
                mentions = _AT_PATTERN.findall(raw)
                if mentions:
                    clean_text = _AT_PATTERN.sub("", raw).strip()
                    if clean_text:
                        self.intention = (self.intention + " " + clean_text).strip()

                    for mention in mentions:
                        self._handle_mention(mention)
                else:
                    # Texto libre sin @ → guardar como intención
                    self.intention = (self.intention + " " + raw).strip()
                    # Intentar búsqueda implícita con las palabras clave
                    words = [w for w in re.split(r'\W+', raw) if len(w) > 3]
                    if words and not self.selected:
                        results = self.searcher.search_multi(words, limit=8)
                        if results:
                            print(f"\n  {DIM}Archivos relacionados con tu input:{NC}")
                            self._show_results(results)
                            self._pick_from(results, optional=True)

                self._show_selected()
            except Exception as e:
                print(f"\n  [!] Error: {e}")

        # Confirmar y ejecutar
        return self._execute()

    # ─── Manejo de @menciones ──────────────────────────────────────────────

    def _handle_mention(self, query: str):
        results = self.searcher.search(query, limit=15)
        if not results:
            print(f"\n  {RED}! No se encontró nada para '@{query}'{NC}")
            return

        if len(results) == 1:
            path = results[0].path
            if path not in self.selected:
                self.selected.append(path)
                print(f"\n  {GREEN}+{NC} {CYAN}{path}{NC}")
            return

        print(f"\n  {YELLOW}Resultados para '@{query}':{NC}\n")
        self._show_results(results)
        self._pick_from(results)

    def _show_results(self, results: list):
        for i, r in enumerate(results, 1):
            tag = _lang_tag(r.language)
            match_label = f"  {DIM}({r.match_type}: {r.matched_on}){NC}" if r.match_type == "symbol" else ""
            print(f"  {YELLOW}{i:>3}{NC}. {CYAN}{r.path}{NC} {tag}{match_label}")

    def _pick_from(self, results: list, optional: bool = False):
        hint = "Enter para omitir" if optional else "Enter para tomar el primero"
        try:
            raw = input(f"\n  Seleccioná ({hint}, ej: 1,3 o 1-4): ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if not raw:
            if not optional and results:
                path = results[0].path
                if path not in self.selected:
                    self.selected.append(path)
            return

        indices = _parse_selection(raw, len(results))
        for idx in indices:
            path = results[idx].path
            if path not in self.selected:
                self.selected.append(path)

    # ─── Visualización ────────────────────────────────────────────────────

    def _header(self):
        print(f"\n{BLUE}╔══════════════════════════════════════════╗")
        print(f"║      cipher impact — modo interactivo     ║")
        print(f"╚══════════════════════════════════════════╝{NC}")
        print(f"\n  Repo: {CYAN}{self.repo_name}{NC}"
              f"  ({self.graph.node_count} archivos · {self.graph.edge_count} aristas)\n")
        print(f"  {DIM}Escribí tu intención o usá {NC}{YELLOW}@nombre{NC}{DIM} para buscar archivos.")
        print(f"  {NC}{YELLOW}/list{NC}{DIM} → ver selección · {NC}{YELLOW}/cls{NC}{DIM} → limpiar · "
              f"{NC}{YELLOW}Enter{NC}{DIM} (con archivos) → ejecutar{NC}")

    def _show_selected(self):
        if not self.selected:
            return
        print(f"\n  {BLUE}Contexto seleccionado:{NC}")
        for path in self.selected:
            print(f"    {GREEN}+{NC} {path}")
        if self.intention:
            print(f"  {BLUE}Intención:{NC} {DIM}{self.intention}{NC}")

    # ─── Ejecución del análisis ────────────────────────────────────────────

    def _execute(self) -> bool:
        if not self.selected:
            print(f"\n  {YELLOW}No hay archivos seleccionados.{NC}\n")
            return False

        print(f"\n  {YELLOW}▸ Analizando impacto...{NC}\n")

        # BFS en cada archivo seleccionado, unificar resultados
        all_impact: dict = {}   # path → ImpactEntry (profundidad mínima)
        for target in self.selected:
            if target not in self.graph.nodes:
                continue
            for entry in self.graph.impact_set(target, max_depth=self.max_depth):
                if entry.file_path not in all_impact:
                    all_impact[entry.file_path] = entry
                elif entry.depth < all_impact[entry.file_path].depth:
                    all_impact[entry.file_path] = entry

        impact_list = sorted(all_impact.values(), key=lambda e: (e.depth, e.file_path))

        # Calcular métricas de riesgo
        risk, risk_color = _risk(len(impact_list), impact_list)
        test_files = [e.file_path for e in impact_list if _is_test(e.file_path)]
        config_files = [e.file_path for e in impact_list if _is_config(e.file_path)]

        # Módulos afectados (directorios top-2)
        modules = _top_modules(impact_list)

        # Output ─────────────────────────────────────────────────────────
        print(f"{BLUE}{'─'*50}{NC}")
        print(f"\n  {BLUE}IMPACT SUMMARY{NC}\n")

        if self.intention:
            print(f"  {DIM}Intención: {self.intention}{NC}\n")

        print(f"  Archivos analizados : {len(self.selected)}")
        print(f"  Archivos afectados  : {len(impact_list)}")
        print(f"  Nivel de riesgo     : {risk_color}{risk}{NC}\n")

        if modules:
            print(f"  {BLUE}Módulos afectados:{NC}")
            for mod, count in modules:
                print(f"    {CYAN}{mod}{NC}  ({count} archivo{'s' if count > 1 else ''})")
            print()

        if test_files:
            print(f"  {YELLOW}⚠ Tests en el impact set:{NC}")
            for t in test_files[:5]:
                print(f"    {t}")
            if len(test_files) > 5:
                print(f"    ... y {len(test_files)-5} más")
            print()

        if config_files:
            print(f"  {RED}⚠ Archivos de configuración/schema afectados:{NC}")
            for c in config_files[:3]:
                print(f"    {c}")
            print()

        # Archivos afectados por depth
        if impact_list:
            print(f"  {BLUE}Archivos afectados por profundidad:{NC}\n")
            current_depth = None
            for entry in impact_list:
                if entry.depth != current_depth:
                    current_depth = entry.depth
                    print(f"  {YELLOW}depth {current_depth}{NC}")
                via_str = f"  {DIM}via {' → '.join(entry.via[-2:])}{NC}" if entry.via else ""
                print(f"    {GREEN}{entry.file_path}{NC}{via_str}")
        else:
            print(f"  {YELLOW}Ningún archivo depende de los seleccionados.{NC}")

        print(f"\n{BLUE}{'─'*50}{NC}\n")
        return True


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_selection(raw: str, max_n: int) -> list:
    """Parsea '1,3,5' o '1-4' o '2' → lista de índices 0-based."""
    indices = []
    for part in re.split(r'[,\s]+', raw.strip()):
        part = part.strip()
        if '-' in part:
            try:
                a, b = part.split('-', 1)
                for i in range(int(a), int(b) + 1):
                    if 1 <= i <= max_n:
                        indices.append(i - 1)
            except ValueError:
                pass
        else:
            try:
                i = int(part)
                if 1 <= i <= max_n:
                    indices.append(i - 1)
            except ValueError:
                pass
    return list(dict.fromkeys(indices))  # dedup manteniendo orden


def _lang_tag(language: str) -> str:
    colors = {
        "python": f"{DIM}[py]{NC}",
        "typescript": f"{DIM}[ts]{NC}",
        "javascript": f"{DIM}[js]{NC}",
        "go": f"{DIM}[go]{NC}",
    }
    return colors.get(language, f"{DIM}[{language[:3]}]{NC}")


def _risk(count: int, impact_list: list) -> tuple[str, str]:
    if count == 0:     return "ninguno", GREEN
    if count <= 3:     return "bajo",    GREEN
    if count <= 10:    return "medio",   YELLOW
    if count <= 30:    return "alto",    f'\033[0;33m'
    return "crítico", RED


def _is_test(path: str) -> bool:
    p = path.lower()
    return any(x in p for x in ('.test.', '.spec.', 'test_', '_test.', '/tests/', '/test/'))


def _is_config(path: str) -> bool:
    p = path.lower()
    return any(x in p for x in (
        'schema', 'config', 'settings', 'migration', 'seed',
        '.env', 'docker', 'makefile', 'requirements', 'package.json',
    ))


def _top_modules(impact_list: list) -> list:
    """Extrae los módulos (dirs) más afectados."""
    counts: dict = {}
    for entry in impact_list:
        parts = entry.file_path.split('/')
        mod = '/'.join(parts[:min(2, len(parts)-1)]) if len(parts) > 1 else parts[0]
        counts[mod] = counts.get(mod, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
