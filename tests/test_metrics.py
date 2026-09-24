"""Return statistics: hand-worked metrics (real API shapes)."""

import math

import pytest

from trade_swing.metrics import (
    cagr,
    expectancy,
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    summarize,
    win_rate,
)


def test_cagr_hand():
    # 100 -> 110 over exactly one year
    assert cagr([100.0, 110.0], periods_per_year=1) == pytest.approx(0.10)


def test_cagr_multi_year():
    # 100 -> 110 -> 121 over two years: 10% annualized
    assert cagr([100.0, 110.0, 121.0], periods_per_year=1) == pytest.approx(0.10)


def test_sharpe_needs_minimum():
    assert sharpe_ratio([100.0]) is None
    assert sharpe_ratio([100.0, 100.0, 100.0]) is None  # zero-vol -> None


def test_sharpe_positive_trend():
    eq = [100.0]
    for i in range(60):
        eq.append(eq[-1] * (1.001 if i % 2 == 0 else 1.0005))
    assert sharpe_ratio(eq) > 0


def test_max_drawdown_hand():
    # 100 -> 120 -> 90 -> 100 : worst peak-to-trough -25%
    dd = max_drawdown([100.0, 120.0, 90.0, 100.0])
    assert dd["max_drawdown"] == pytest.approx(-0.25)
    assert dd["peak_idx"] == 1 and dd["trough_idx"] == 2


def test_max_drawdown_none():
    assert max_drawdown([100.0, 110.0, 120.0])["max_drawdown"] == 0.0


def _trades():
    return [{"pnl_net": 10.0}, {"pnl_net": -5.0}, {"pnl_net": 3.0}]


def test_win_rate():
    assert win_rate(_trades()) == pytest.approx(2 / 3)
    assert win_rate([]) is None


def test_profit_factor():
    assert profit_factor(_trades()) == pytest.approx(13.0 / 5.0)
    assert profit_factor([{"pnl_net": 10.0}]) == math.inf
    assert profit_factor([{"pnl_net": -5.0}]) == 0.0
    assert profit_factor([]) is None


def test_expectancy():
    assert expectancy(_trades()) == pytest.approx(8.0 / 3.0)
    assert expectancy([]) is None


def test_summarize_schema():
    eq = [100_000.0 + i * 100 for i in range(60)]
    s = summarize(eq, _trades())
    assert {"total_return", "cagr", "sharpe_ratio", "max_drawdown",
            "num_trades", "win_rate", "profit_factor", "expectancy"} <= set(s)
    assert s["num_trades"] == 3.0
    assert isinstance(s["max_drawdown"], float)
