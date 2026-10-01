from dataclasses import dataclass
from typing import Protocol


@dataclass
class ImageInput:
    mime: str
    data: bytes


class ProviderError(Exception):
    """Provider unavailable / timeout / auth failure (distinct from malformed output)."""


class LLMProvider(Protocol):
    name: str
    model: str | None

    def complete_json(self, system: str, user: str, json_schema: dict, images: list[ImageInput] | None = None) -> str:
        """Return raw model text that should contain one JSON object."""
        ...
