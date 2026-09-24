"""ValidationReport: schema version, JSON round-trip, honest limitations."""

import json

import pytest

from trade_swing.report import LIMITATIONS, build_report, report_to_json
from conftest import HAS_OVERFIT

needs_overfit = pytest.mark.skipif(not HAS_OVERFIT,
                                   reason="trade-overfit not installed")


@needs_overfit
def test_build_report_end_to_end(tmp_path):
    from trade_swing.backtest import run_backtest
    from trade_swing.demo import BASKETS, demo_bars, demo_benchmark
    from trade_swing.strategy import SwingConfig
    from trade_swing.validate import run_validation
    bars = demo_bars()
    sub = {s: bars[s] for s in BASKETS["trend"]}
    bt = run_backtest(sub, config=SwingConfig())
    val = run_validation(bt, benchmark_returns=demo_benchmark(sub, BASKETS["trend"]))
    r = build_report(bt, val)
    assert r["schema_version"] == 1
    assert r["strategy"]["name"] == "swing-trend"
    assert r["validation"]["status"] == "PASS"
    assert r["backtest"]["engine"] in ("trade-backtest", "internal-fallback")
    assert r["backtest"]["n_trades"] > 0
    p = tmp_path / "report.json"
    p.write_text(report_to_json(r))
    assert json.loads(p.read_text())["schema_version"] == 1  # round-trip


def test_limitations_are_explicit():
    text = " ".join(LIMITATIONS).lower()
    assert "synthetic" in text
    assert "chop" in text
    assert "not that the strategy makes money" in text
    assert any("overfitting" in line for line in LIMITATIONS)


def test_report_schema_keys():
    r = build_report(
        {"engine": "internal-fallback", "config": {"fast": 20},
         "metrics": {}, "trades": [], "open_positions": [],
         "provenance": {"source": "unit-test"}},
        {"status": "FAIL", "gates": [], "warnings": []},
    )
    assert {"schema_version", "generated_utc", "strategy", "data_provenance",
            "backtest", "costs", "validation", "limitations"} <= set(r)
    assert r["strategy"]["config"]["fast"] == 20
    assert r["data_provenance"]["source"] == "unit-test"
