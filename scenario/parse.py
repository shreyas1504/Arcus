"""Question parsing with Nemotron (PLAN.md 3b). Contract stub: implemented by Cursor in U1.

The model only interprets the question into a ParsedScenario. It never returns numbers.
Temperature 0, PARSE_TIMEOUT_S timeout, cached by SHA256 of the normalized text
(whitespace collapsed, lowercased). Any failure (timeout, invalid JSON, a category
outside the enum, validation error) returns the fallback:
    ParsedScenario(search_text=<normalized text>, fallback=True)
with no category, regions, sectors or companies.
"""

from __future__ import annotations

from typing import Any

from scenario.schemas import ParsedScenario

PARSE_TIMEOUT_S = 15.0


def parse_scenario(text: str, *, client: Any | None = None) -> ParsedScenario:
    """Interpret `text`. `client` is an OpenAI-compatible client (tests pass a fake)."""
    raise NotImplementedError


def clear_cache() -> None:
    raise NotImplementedError
