"""Validation: gate behavior, demo discrimination, SKIPPED fallback."""

import pytest

from trade_swing.backtest import run_backtest
from trade_swing.demo import BASKETS, demo_bars, demo_benchmark, run_demo
from trade_swing.strategy import SwingConfig
from trade_swing.validate import run_validation
from conftest import HAS_OVERFIT, make_bars

needs_overfit = pytest.mark.skipif(not HAS_OVERFIT,
                                   reason="trade-overfit not installed")


@needs_overfit
def test_demo_trend_passes():
    v = run_demo()["trend"]["validation"]
    assert v["status"] == "PASS"
    assert all(g["verdict"] == "PASS" for g in v["gates"])
    assert not v["warnings"]


@needs_overfit
def test_demo_chop_fails_or_warns():
    v = run_demo()["chop"]["validation"]
    assert v["status"] in ("FAIL", "WARN")
    assert any(g["verdict"] == "FAIL" for g in v["gates"])


@needs_overfit
def test_gates_discriminate_trend_from_chop():
    trend = run_demo()["trend"]["validation"]
    chop = run_demo()["chop"]["validation"]
    t = {g["name"]: g["value"] for g in trend["gates"]}
    c = {g["name"]: g["value"] for g in chop["gates"]}
    assert t["deflated_sharpe"] > c["deflated_sharpe"]
    assert t["oos_sharpe"] > c["oos_sharpe"]
    assert t["regime_stability"] > c["regime_stability"]


@needs_overfit
def test_gate_margin_fields():
    v = run_demo()["trend"]["validation"]
    for g in v["gates"]:
        assert set(g) >= {"name", "verdict", "metric", "op", "value",
                          "threshold", "margin", "description"}
        assert g["verdict"] in ("PASS", "WARN", "FAIL", "SKIPPED")
        if g["value"] is not None:
            expected = (g["value"] - g["threshold"]
                        if g["op"] in ("gte", "gt")
                        else g["threshold"] - g["value"])
            assert g["margin"] == pytest.approx(expected)
            # PASS means a non-negative margin, FAIL a negative one
            assert (g["margin"] >= 0) == (g["verdict"] == "PASS")


@needs_overfit
def test_validation_result_schema():
    v = run_demo()["trend"]["validation"]
    assert set(v) >= {"status", "gates", "warnings"}
    assert v["status"] in ("PASS", "WARN", "FAIL", "SKIPPED")


def test_skipped_without_sibling(monkeypatch):
    """Missing trade-overfit -> every gate SKIPPED, never silent."""
    import trade_swing.validate as val
    monkeypatch.setattr(val, "_try_import_trade_overfit", lambda: None)
    bars = demo_bars()
    sub = {s: bars[s] for s in BASKETS["trend"]}
    bt = run_backtest(sub, config=SwingConfig(), force_engine="internal")
    v = run_validation(bt, benchmark_returns=demo_benchmark(sub, BASKETS["trend"]))
    assert v["status"] == "SKIPPED"
    assert all(g["verdict"] == "SKIPPED" for g in v["gates"])


@needs_overfit
def test_warn_sample_size():
    closes = [100.0] * 10 + [120.0] * 10 + [100.0] * 10 + [120.0] * 10 + [100.0] * 10
    bars = {"T": make_bars(closes)}
    cfg = SwingConfig(fast=2, slow=3, atr_period=2, stop_multiple=100.0)
    bt = run_backtest(bars, config=cfg, force_engine="internal")
    assert len(bt["trades"]) < 30  # the WARN must fire on this fixture
    v = run_validation(bt, benchmark_returns=[0.0] * (len(bt["equity_curve"]) - 1))
    assert "sample_size" in {w["name"] for w in v["warnings"]}


@needs_overfit
def test_warn_cost_drag_and_concentration():
    # one dominant trade + heavy costs relative to gross
    bt = {
        "engine": "internal-fallback",
        "config": {},
        "trades": [
            {"symbol": "T", "entry_date": "2026-01-01", "exit_date": "2026-01-02",
             "entry_price": 100.0, "exit_price": 200.0, "quantity": 1000,
             "pnl_gross": 100_000.0, "cost": 60_000.0, "pnl_net": 40_000.0},
        ],
        "costs": {"n_trades": 1, "total_cost": 60_000.0,
                  "total_pnl_gross": 100_000.0,
                  "total_pnl_net": 40_000.0, "cost_drag": 0.6},
        "equity_curve": [{"date": "2026-01-%02d" % (i + 1),
                           "equity": 100_000.0 + i * 100} for i in range(60)],
    }
    v = run_validation(bt, benchmark_returns=[0.0] * 59)
    names = {w["name"] for w in v["warnings"]}
    assert "cost_drag" in names
    assert "concentration" in names


@needs_overfit
def test_overall_fail_when_any_gate_fails():
    v = run_demo()["chop"]["validation"]
    fails = [g for g in v["gates"] if g["verdict"] == "FAIL"]
    assert fails and v["status"] == "FAIL"
