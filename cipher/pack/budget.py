"""
cipher pack — Token Budget Manager (F3-3)
Gestiona el presupuesto de tokens por proveedor y recorta contenido.

Prioridad de inclusión: target > dependency > context (rules, arch)
"""

PROVIDER_BUDGETS = {
    "claude":  60_000,
    "gemini": 400_000,
    "default": 60_000,
}

# Reservar % del budget para rules + architecture snippet
RULES_BUDGET_RATIO   = 0.05   # 5%
ARCH_BUDGET_RATIO    = 0.05   # 5%
FILES_BUDGET_RATIO   = 0.90   # 90%


def get_budget(provider: str) -> int:
    return PROVIDER_BUDGETS.get(provider.lower(), PROVIDER_BUDGETS["default"])


def estimate_tokens(text: str) -> int:
    """Estimación rápida: ~4 chars por token (heurística estándar)."""
    return max(1, len(text) // 4)


def trim_content(content: str, max_tokens: int) -> tuple[str, int]:
    """
    Recorta content para que no exceda max_tokens.
    Retorna (content_recortado, tokens_usados).
    """
    max_chars = max_tokens * 4
    if len(content) <= max_chars:
        return content, estimate_tokens(content)
    trimmed = content[:max_chars]
    # Cortar en límite de línea para no truncar a mitad de código
    last_newline = trimmed.rfind("\n")
    if last_newline > max_chars * 0.8:
        trimmed = trimmed[:last_newline]
    trimmed += "\n\n... [truncado por budget] ..."
    return trimmed, estimate_tokens(trimmed)


class TokenBudget:
    """Controla cuánto presupuesto de tokens queda."""

    def __init__(self, provider: str):
        self.total = get_budget(provider)
        self.remaining = self.total
        self._used = 0

    @property
    def used(self) -> int:
        return self._used

    def reserve(self, tokens: int) -> bool:
        """Intenta reservar tokens. Retorna True si hay suficiente."""
        if tokens > self.remaining:
            return False
        self.remaining -= tokens
        self._used += tokens
        return True

    def allocate(self, content: str, max_tokens: int | None = None) -> tuple[str, int]:
        """
        Ajusta content al presupuesto disponible (o a max_tokens si se especifica).
        Retorna (content_final, tokens_usados).
        Actualiza el presupuesto restante.
        """
        cap = min(self.remaining, max_tokens) if max_tokens else self.remaining
        if cap <= 0:
            return "", 0
        trimmed, used = trim_content(content, cap)
        self.remaining -= used
        self._used += used
        return trimmed, used

    def files_budget(self) -> int:
        return int(self.total * FILES_BUDGET_RATIO)

    def rules_budget(self) -> int:
        return int(self.total * RULES_BUDGET_RATIO)

    def arch_budget(self) -> int:
        return int(self.total * ARCH_BUDGET_RATIO)
