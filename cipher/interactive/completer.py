"""
cipher interactive — AtMentionCompleter
Completer para prompt_toolkit: activa sugerencias en tiempo real al escribir @query.
"""

from prompt_toolkit.completion import Completer, Completion


class AtMentionCompleter(Completer):
    """
    Activa cuando el cursor está después de un @.
    Muestra archivos/símbolos que coincidan con lo que se tipea.
    Reemplaza @query con @path/completo para que el parser existente lo resuelva.
    """

    def __init__(self, searcher):
        self.searcher = searcher

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # Buscar el @ más reciente sin espacio después
        at_pos = text.rfind("@")
        if at_pos == -1:
            return

        query = text[at_pos + 1:]
        if not query or " " in query:
            return

        results = self.searcher.search(query, limit=10)
        for r in results:
            basename = r.path.split("/")[-1]
            lang_tag = f"[{r.language[:2]}]" if r.language else ""
            display = f"{r.path}"
            meta = lang_tag

            # Reemplaza solo la parte `query` (el @ se mantiene)
            yield Completion(
                r.path,
                start_position=-len(query),
                display=display,
                display_meta=meta,
            )
