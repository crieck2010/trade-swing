"""Backtest: hand-worked series, engine flags, dual-path agreement."""

import pytest

from trade_swing.backtest import run_backtest
from trade_swing.strategy import SwingConfig
from conftest import make_bars, HAS_BACKTEST


def _hand_bars():
    # entry signal d5 (2026-01-06) -> fill d6 open=110;
    # exit signal d11 (2026-01-12) -> fill d12 open=130
    closes = [100, 100, 100, 100, 100, 110, 120, 130, 140, 150,
              140, 130, 120, 110, 100]
    return {"T": make_bars(closes)}


def _cfg():
    return SwingConfig(fast=2, slow=3, atr_period=2, stop_multiple=100.0,
                       risk_per_trade=0.02, max_position_pct=1.0)


def test_hand_worked_series():
    # equity at signal 100_000; ATR[5]=6.0 -> floor(2000/600)=3 shares;
    # cap floor(100000/110)=909 -> 3 shares
    res = run_backtest(_hand_bars(), config=_cfg(), force_engine="internal")
    assert res["engine"] == "internal-fallback"
    assert len(res["trades"]) == 1
    t = res["trades"][0]
    assert t["entry_date"] == "2026-01-07" and t["entry_price"] == 110.0
    assert t["exit_date"] == "2026-01-13" and t["exit_price"] == 130.0
    assert t["quantity"] == 3
    assert t["pnl_gross"] == pytest.approx(60.0)
    assert t["pnl_net"] == pytest.approx(59.538)
    assert res["final_equity"] == pytest.approx(100_059.538)
    assert res["trades"][0]["symbol"] == "T"


def test_no_lookahead_fill():
    # fills happen on the bar AFTER the signal bar, at its open
    res = run_backtest(_hand_bars(), config=_cfg(), force_engine="internal")
    t = res["trades"][0]
    bars = _hand_bars()["T"]
    fill_day = next(b for b in bars if b["date"] == "2026-01-07")
    assert t["entry_price"] == fill_day["open"]
    # the signal fired on the prior bar (cross_up at 2026-01-06)
    assert t["entry_date"] == "2026-01-07"


def test_costs_applied():
    res = run_backtest(_hand_bars(), config=_cfg(), force_engine="internal")
    t = res["trades"][0]
    assert t["pnl_net"] < t["pnl_gross"]
    assert t["cost"] > 0


def test_metrics_present():
    res = run_backtest(_hand_bars(), config=_cfg(), force_engine="internal")
    m = res["metrics"]
    assert {"total_return", "cagr", "sharpe_ratio", "max_drawdown",
            "num_trades", "win_rate", "profit_factor", "expectancy"} <= set(m)
    assert m["win_rate"] == 1.0


def test_empty_raises():
    with pytest.raises(ValueError):
        run_backtest({})


def test_provenance_passthrough():
    prov = {"source": "unit-test"}
    res = run_backtest(_hand_bars(), config=_cfg(), force_engine="internal",
                       provenance=prov)
    assert res["provenance"] == prov


def test_engine_flag_internal_forced():
    res = run_backtest(_hand_bars(), config=_cfg(), force_engine="internal")
    assert res["engine"] == "internal-fallback"


@pytest.mark.skipif(not HAS_BACKTEST, reason="trade-backtest not installed")
def test_sibling_engine_agrees():
    """Both engines must agree on the hand-worked series."""
    bars = _hand_bars()
    a = run_backtest(bars, config=_cfg(), force_engine="internal")
    b = run_backtest(bars, config=_cfg(), force_engine="trade-backtest")
    assert b["engine"] == "trade-backtest"
    assert len(a["trades"]) == len(b["trades"]) == 1
    ta, tb = a["trades"][0], b["trades"][0]
    assert ta["quantity"] == tb["quantity"] == 3
    assert ta["entry_price"] == tb["entry_price"] == 110.0
    assert ta["exit_price"] == tb["exit_price"] == 130.0
    assert a["final_equity"] == pytest.approx(b["final_equity"], rel=1e-9)
