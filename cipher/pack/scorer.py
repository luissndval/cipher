"""
cipher pack — Scorer (F3-2, paso 3)
Puntúa archivos del índice por relevancia a una descripción de tarea.

Criterios (sin LLM):
  +2.0  por cada palabra de la tarea que aparece en el path del archivo
  +1.0  por cada palabra de la tarea que aparece en un nombre de símbolo
  +0.5  si el archivo es de los más importados en el grafo (top 20%)
  +0.3  si el archivo tiene símbolos exportados (no solo importa)
"""

import re
from cipher.index.schema import FileIndex
from cipher.graph.schema import DependencyGraph


def _task_tokens(task_description: str) -> set:
    """Extrae palabras significativas de la descripción de tarea."""
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", task_description.lower())
    # Filtrar stop words comunes
    stop = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
        "is", "it", "be", "as", "by", "with", "from", "that", "this", "have",
        "add", "fix", "update", "change", "create", "implement", "make", "get",
        "use", "new", "the", "need", "should", "when", "how", "what", "where",
        "archivo", "archivos", "función", "clase", "método", "módulo", "repo",
    }
    return {w for w in words if len(w) > 2 and w not in stop}


_FILE_EXT_RE = re.compile(
    r"\b([\w][\w\-.]*\.(?:py|ts|js|tsx|jsx|go|java|rb|rs|php|cs|cpp|c|h|kt|swift))\b",
    re.IGNORECASE,
)


def _file_mentions(task_description: str) -> set[str]:
    """Extrae nombres de archivo mencionados explícitamente en la descripción."""
    return {m.lower() for m in _FILE_EXT_RE.findall(task_description)}


def score_files(
    files: list,
    task_description: str,
    graph: DependencyGraph | None = None,
) -> list:
    """
    Puntúa cada FileIndex y retorna lista de (score, FileIndex) ordenada desc.

    Args:
        files: list[FileIndex]
        task_description: descripción libre de la tarea
        graph: opcional — si se provee, usa inbound degree para bonus
    """
    tokens = _task_tokens(task_description)
    mentions = _file_mentions(task_description)

    if not tokens and not mentions:
        # Sin tokens útiles: devolver todos con score 0
        return [(0.0, f) for f in files]

    # Calcular inbound degrees si hay grafo
    inbound: dict[str, int] = {}
    high_inbound: set = set()
    if graph:
        for path in graph.nodes:
            deps = graph.dependents_of(path)
            inbound[path] = len(deps)
        if inbound:
            threshold = sorted(inbound.values(), reverse=True)
            top_20_idx = max(1, len(threshold) // 5)
            cutoff = threshold[top_20_idx - 1]
            # Mínimo absoluto de 3 inbound para evitar falsos positivos en repos pequeños
            high_inbound = {p for p, c in inbound.items() if c >= cutoff and c >= 3}

    scored = []
    for file_index in files:
        s = _score_one(file_index, tokens, high_inbound, mentions)
        scored.append((s, file_index))

    return sorted(scored, key=lambda x: x[0], reverse=True)


def _score_one(
    file_index: FileIndex,
    tokens: set,
    high_inbound: set,
    mentions: set | None = None,
) -> float:
    score = 0.0
    path_lower = file_index.path.lower()
    basename = path_lower.split("/")[-1].split("\\")[-1]

    # Boost fuerte: nombre de archivo mencionado explícitamente (ej: "dashboard.py")
    if mentions:
        for mention in mentions:
            if mention == basename or mention in basename:
                score += 5.0
                break

    # Palabras de la tarea en el path
    for token in tokens:
        if token in path_lower:
            score += 2.0

    # Palabras de la tarea en nombres de símbolos
    symbol_names_lower = {s.name.lower() for s in file_index.symbols}
    for token in tokens:
        for sname in symbol_names_lower:
            if token in sname:
                score += 1.0
                break  # una vez por token

    # Bonus: archivo muy importado
    if file_index.path in high_inbound:
        score += 0.5

    # Bonus: tiene símbolos definidos (no solo importador)
    if file_index.symbols:
        score += 0.3

    return score
