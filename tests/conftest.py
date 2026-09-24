"""Shared fixtures: sibling repos on sys.path when present (real-path tests),
hand-worked bar builders, and importorskip helpers."""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE_ROOT = os.path.dirname(REPO_ROOT)


def _maybe_add(path: str) -> bool:
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)
        return True
    return False


HAS_BACKTEST = _maybe_add(os.path.join(SUITE_ROOT, "trade-backtest", "src"))
HAS_OVERFIT = _maybe_add(os.path.join(SUITE_ROOT, "trade-overfit", "src"))

try:
    import trade_backtest  # noqa: F401
    HAS_BACKTEST = True
except ImportError:
    HAS_BACKTEST = False

try:
    import trade_overfit  # noqa: F401
    HAS_OVERFIT = True
except ImportError:
    HAS_OVERFIT = False


def make_bars(closes, start="2026-01-01", opens=None):
    """Hand-worked bars: H = max(O,C)+0.5, L = min(O,C)-0.5.

    ``opens`` defaults to previous close (realistic gaps); pass
    ``opens="flat"`` for O=C.
    """
    from datetime import date, timedelta
    d0 = date.fromisoformat(start)
    bars = []
    prev = closes[0]
    for i, c in enumerate(closes):
        o = c if opens == "flat" else (prev if i else closes[0])
        bars.append({
            "date": (d0 + timedelta(days=i)).isoformat(),
            "open": o,
            "high": max(o, c) + 0.5,
            "low": min(o, c) - 0.5,
            "close": c,
            "volume": 1_000_000,
        })
        prev = c
    return bars
