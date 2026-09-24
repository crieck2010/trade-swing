"""Strategy math: MA, Wilder ATR, cross detection, stops, gating."""

import pytest

from trade_swing.strategy import (
    SwingConfig,
    SwingTrendStrategy,
    generate_signals,
    simple_ma,
    true_range,
    wilder_atr,
)
from conftest import make_bars


# --- moving average --------------------------------------------------------

def test_simple_ma_hand_computed():
    assert simple_ma([10, 11, 12, 13, 14], 3) == [None, None, 11.0, 12.0, 13.0]


def test_simple_ma_n1_no_warmup():
    assert simple_ma([5.0, 6.0], 1) == [5.0, 6.0]


def test_simple_ma_bad_n():
    with pytest.raises(ValueError):
        simple_ma([1.0], 0)


# --- true range / ATR ------------------------------------------------------

def test_true_range_first_bar():
    bars = make_bars([100.0], opens="flat")
    assert true_range(bars) == [1.0]  # high - low


def test_true_range_gap_up():
    bars = make_bars([100.0, 110.0], opens="flat")
    # bar1: max(1.0, |110.5-100|, |109.5-100|) = 10.5
    assert true_range(bars)[1] == pytest.approx(10.5)


def test_wilder_atr_hand_computed():
    # closes chosen so TRs are 7, 5, 4, 6 (hand-computed in test comments)
    bars = [
        {"date": "2026-01-01", "open": 100, "high": 105, "low": 98, "close": 102},
        {"date": "2026-01-02", "open": 102, "high": 106, "low": 101, "close": 105},
        {"date": "2026-01-03", "open": 105, "high": 107, "low": 103, "close": 104},
        {"date": "2026-01-04", "open": 104, "high": 110, "low": 104, "close": 109},
    ]
    atr = wilder_atr(bars, 3)
    assert atr[0] is None and atr[1] is None
    assert atr[2] == pytest.approx((7 + 5 + 4) / 3)          # seeded mean
    assert atr[3] == pytest.approx((atr[2] * 2 + 6) / 3)     # Wilder smooth


def test_wilder_atr_short_series():
    bars = make_bars([100.0, 101.0])
    assert wilder_atr(bars, 5) == [None, None]


# --- cross detection -------------------------------------------------------

def _cross_bars():
    # fast(2)/slow(3): cross UP at index 4 (fast 15 > slow 13.33, prev 10 <= 10)
    return make_bars([10, 10, 10, 10, 20, 20], opens="flat")


def test_cross_up_entry():
    cfg = SwingConfig(fast=2, slow=3, atr_period=2, stop_multiple=100.0)
    sigs = generate_signals(_cross_bars(), cfg)
    entries = [s for s in sigs if s["signal"] == "enter_long"]
    assert len(entries) == 1
    assert entries[0]["date"] == "2026-01-05"  # index 4
    assert entries[0]["in_position"] is True


def test_cross_down_exit():
    bars = make_bars([10, 10, 10, 10, 20, 20, 20, 5, 5, 5], opens="flat")
    cfg = SwingConfig(fast=2, slow=3, atr_period=2, stop_multiple=100.0)
    sigs = generate_signals(bars, cfg)
    exits = [s for s in sigs if s["signal"] == "exit_long"]
    assert len(exits) == 1
    assert exits[0]["in_position"] is False


def test_no_lookahead():
    """Signals on a truncated series match the full series' prefix."""
    bars = make_bars([10, 10, 10, 10, 20, 20, 18, 22, 25, 15, 12, 14])
    cfg = SwingConfig(fast=2, slow=3, atr_period=2, stop_multiple=100.0)
    full = generate_signals(bars, cfg)
    for cut in (6, 8, 10):
        trunc = generate_signals(bars[:cut], cfg)
        assert [s["signal"] for s in trunc] == \
            [s["signal"] for s in full[:len(trunc)]]
        assert [s["date"] for s in trunc] == \
            [s["date"] for s in full[:len(trunc)]]


# --- trailing stop ---------------------------------------------------------

def test_trailing_stop_exit_and_reentry():
    # rally, then a sharp drop through the stop, then recovery above it
    closes = [100] * 8 + [110, 120, 130, 140,  # rally
                          100, 95,              # crash through stop
                          150, 160, 170]        # recovery
    bars = make_bars(closes, opens="flat")
    cfg = SwingConfig(fast=2, slow=4, atr_period=2, stop_multiple=2.0)
    sigs = generate_signals(bars, cfg)
    by_date = {s["date"]: s for s in sigs}
    exits = [s for s in sigs if s["signal"] == "exit_long"]
    assert exits, "expected a stop-out"
    # after the stop-out, recovery above the frozen stop re-enters
    entries = [s for s in sigs if s["signal"] == "enter_long"]
    assert len(entries) >= 2, "expected initial entry + re-entry"


def test_stop_trails_up_only():
    closes = [100] * 6 + [110, 115, 112, 120, 125]
    bars = make_bars(closes, opens="flat")
    cfg = SwingConfig(fast=2, slow=3, atr_period=2, stop_multiple=2.0)
    sigs = generate_signals(bars, cfg)
    stops = [s["stop"] for s in sigs if s["in_position"] and s["stop"] is not None]
    assert stops == sorted(stops), "trailing stop must never move down"


def test_cross_down_clears_reentry():
    # after a cross-down exit the re-entry reference is cleared: a later
    # rally with fast still below slow must NOT re-enter without a cross
    bars = make_bars([10, 10, 10, 10, 20, 20, 5, 5, 5, 5], opens="flat")
    cfg = SwingConfig(fast=2, slow=3, atr_period=2, stop_multiple=100.0)
    sigs = generate_signals(bars, cfg)
    entries = [s for s in sigs if s["signal"] == "enter_long"]
    exits = [s for s in sigs if s["signal"] == "exit_long"]
    assert len(entries) == 1 and len(exits) == 1
    assert sigs[-1]["stop"] is None  # no stale re-entry reference


# --- regime gating ---------------------------------------------------------

def test_regime_gating_suppresses_entries():
    bars = _cross_bars()
    cfg = SwingConfig(fast=2, slow=3, atr_period=2, stop_multiple=100.0,
                      regime_min_conviction=30.0)
    convictions = {b["date"]: 10.0 for b in bars}  # bearish regime
    sigs = generate_signals(bars, cfg, convictions)
    assert not [s for s in sigs if s["signal"] == "enter_long"]
    assert any(s["conviction_gated"] for s in sigs)


def test_regime_gating_allows_exits():
    bars = make_bars([10, 10, 10, 10, 20, 20, 20, 5, 5, 5], opens="flat")
    cfg = SwingConfig(fast=2, slow=3, atr_period=2, stop_multiple=100.0,
                      regime_min_conviction=30.0)
    # enter in a permissive regime, then regime turns hostile
    dates = [b["date"] for b in bars]
    convictions = {d: (80.0 if d < "2026-01-07" else 10.0) for d in dates}
    sigs = generate_signals(bars, cfg, convictions)
    assert [s for s in sigs if s["signal"] == "enter_long"]
    assert [s for s in sigs if s["signal"] == "exit_long"]


# --- config / plumbing -----------------------------------------------------

def test_config_validation():
    with pytest.raises(ValueError):
        SwingConfig(fast=50, slow=20)
    with pytest.raises(ValueError):
        SwingConfig(risk_per_trade=0.0)


def test_empty_bars():
    assert generate_signals([], SwingConfig()) == []


def test_signal_schema():
    sigs = generate_signals(_cross_bars(),
                            SwingConfig(fast=2, slow=3, atr_period=2))
    for s in sigs:
        assert set(s) == {"date", "signal", "fast_ma", "slow_ma", "atr",
                          "stop", "in_position", "conviction_gated"}
        assert s["signal"] in ("enter_long", "exit_long", "flat")


def test_strategy_wrapper_matches_function():
    bars = _cross_bars()
    cfg = SwingConfig(fast=2, slow=3, atr_period=2)
    assert SwingTrendStrategy(cfg).signals(bars) == generate_signals(bars, cfg)
