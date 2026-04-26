"""Fuzzy search helpers for varieties and products."""
from __future__ import annotations

from thefuzz import fuzz, process


def _normalize(s: str) -> str:
    return s.lower().strip()


def fuzzy_find(
    query: str,
    items: list[dict],
    name_key: str = "name",
    limit: int = 5,
    direct_threshold: int = 85,
    suggest_threshold: int = 55,
) -> tuple[dict | None, list[dict]]:
    """
    Returns (direct_match_or_None, list_of_suggestions).
    If score >= direct_threshold → direct match returned, suggestions empty.
    If score >= suggest_threshold → suggestions list returned, direct None.
    """
    if not items:
        return None, []

    q = _normalize(query)
    choices = {_normalize(item[name_key]): item for item in items}

    results = process.extractBests(
        q, list(choices.keys()), scorer=fuzz.partial_ratio, limit=limit, score_cutoff=suggest_threshold
    )

    if not results:
        return None, []

    best_name, best_score = results[0]
    best_item = choices[best_name]

    if best_score >= direct_threshold:
        return best_item, []

    suggestions = [choices[name] for name, _ in results]
    return None, suggestions


def fuzzy_find_variety(query: str, varieties: list[dict]) -> tuple[dict | None, list[dict]]:
    return fuzzy_find(query, varieties, name_key="name")


def fuzzy_find_product(query: str, products: list[dict]) -> tuple[dict | None, list[dict]]:
    return fuzzy_find(query, products, name_key="name")
