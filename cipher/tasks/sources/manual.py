"""
cipher tasks — ManualSource (F4-2)
Fuente de tickets creados directamente desde la CLI.
"""

from cipher.tasks.sources.base import TicketSource, RawTicket


class ManualSource(TicketSource):
    """Crea un RawTicket a partir de input directo del usuario."""

    @property
    def name(self) -> str:
        return "manual"

    def fetch(self, ref: str) -> RawTicket:
        """
        ref: descripción libre de la tarea.
        Si contiene ':' se interpreta como 'título: descripción'.
        """
        if ":" in ref:
            title, _, description = ref.partition(":")
            title = title.strip()
            description = description.strip()
        else:
            title = ref.strip()
            description = ""

        return RawTicket(
            title=title,
            description=description,
            source="manual",
            source_ref="",
            labels=[],
            extra={},
        )
