"""
cipher tasks — TicketSource base (F4-2)
Contrato para fuentes de tickets externos.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawTicket:
    """Ticket crudo antes de ser convertido a Task."""
    title: str
    description: str
    source: str        # "manual" | "github" | "linear"
    source_ref: str    # URL o ID original
    labels: list       # etiquetas del ticket (pueden ayudar a detectar tipo)
    extra: dict        # metadata adicional dependiente de la fuente


class TicketSource(ABC):
    """Interfaz para importar tickets desde sistemas externos."""

    @abstractmethod
    def fetch(self, ref: str) -> RawTicket:
        """
        Obtiene un ticket a partir de una referencia (URL, ID, etc.).
        Lanza ValueError si no puede obtener el ticket.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del source (e.g. 'github', 'linear')."""
        ...
