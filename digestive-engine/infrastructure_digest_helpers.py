"""Infrastructure improvement digestion helpers.
Proposed by org-003 at 2026-05-17T00:27:15.630278+00:00.
"""
from __future__ import annotations


def estimate_improvement_score(result: dict) -> int:
    base = int(result.get("magnitude", 0))
    if result.get("dry_run"):
        return max(0, base - 75)
    return base + 50
