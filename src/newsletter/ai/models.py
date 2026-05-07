from __future__ import annotations

from typing import TypedDict


class ScoredItem(TypedDict, total=False):
    source: str
    title: str
    url: str
    rank: int
    summary: str
    fetched_at: str
    meta: dict
    ai_score: float
    ai_summary: str