"""Template narrative (PLAN.md 3d). Contract stub: implemented by Cursor in U2.

Fills a fixed template using only values already in the response. Every number in
the text must appear in the response fields (formatted). No model call, no advice
words. A low-confidence response gets the "no close precedent" sentence.
"""

from __future__ import annotations

from scenario.schemas import WhatIfResponse


def render(response: WhatIfResponse) -> str:
    """Return the narrative for a response whose `narrative` field is still empty."""
    raise NotImplementedError
