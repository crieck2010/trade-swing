"""Demo: determinism, baskets, benchmark."""

from trade_swing.demo import (
    BASKETS,
    demo_bars,
    demo_benchmark,
    run_demo,
)

N_DAYS = 750


def test_deterministic_same_seed():
    a, b = demo_bars(seed=7), demo_bars(seed=7)
    assert a["TREND_A"] == b["TREND_A"]


def test_different_seeds_differ():
    a, b = demo_bars(seed=7), demo_bars(seed=8)
    assert a["TREND_A"] != b["TREND_A"]


def test_basket_membership():
    bars = demo_bars()
    for basket, symbols in BASKETS.items():
        assert set(symbols) <= set(bars)
    assert BASKETS["trend"] and BASKETS["chop"]


def test_bar_count():
    bars = demo_bars()
    assert all(len(v) == N_DAYS for v in bars.values())


def test_benchmark_alignment():
    bars = demo_bars()
    bench = demo_benchmark(bars, BASKETS["trend"])
    assert len(bench) == N_DAYS - 1


def test_run_demo_keys():
    # run_demo returns one ValidationReport per basket
    demo = run_demo()
    assert set(demo) == {"trend", "chop"}
    for report in demo.values():
        assert {"schema_version", "generated_utc", "strategy",
                "data_provenance", "backtest", "costs", "validation",
                "limitations"} <= set(report)
        assert report["validation"]["status"] in ("PASS", "WARN", "FAIL",
                                                  "SKIPPED")


def test_bar_ohlc_invariants():
    for bars in demo_bars().values():
        for b in bars:
            assert b["low"] <= min(b["open"], b["close"])
            assert b["high"] >= max(b["open"], b["close"])
