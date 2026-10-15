"""Providers voor gestructureerde modeloutput."""

from typing import Protocol


class Provider(Protocol):
    def generate(self, payload: str, schema: dict, system_prompt: str) -> str: ...


class ProviderError(RuntimeError):
    """Veilige foutcode zonder prompt, response of netwerkexceptiontekst."""
