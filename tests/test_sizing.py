"""ATR position sizing: formula, cap, edges.

Signature: atr_position_size(equity, atr, stop_multiple, risk_per_trade,
price, max_position_pct=0.25).
"""

import pytest

from trade_swing.sizing import atr_position_size


def test_formula():
    # floor((100000 * 0.01) / (2.0 * 3.0)) = floor(166.67) = 166;
    # cap floor(100000 * 0.25 / 50) = 500 -> 166
    assert atr_position_size(100_000, 2.0, 3.0, 0.01, 50.0, 0.25) == 166


def test_cap_binds():
    # risk leg wants floor(5000 / 1.5) = 3333, cap allows only 500
    assert atr_position_size(100_000, 0.5, 3.0, 0.05, 50.0, 0.25) == 500


def test_zero_atr_returns_zero():
    assert atr_position_size(100_000, 0.0, 3.0, 0.01, 50.0, 0.25) == 0


def test_zero_equity_returns_zero():
    assert atr_position_size(0.0, 2.0, 3.0, 0.01, 50.0, 0.25) == 0


def test_invalid_risk_raises():
    with pytest.raises(ValueError):
        atr_position_size(100_000, 2.0, 3.0, 0.0, 50.0, 0.25)
    with pytest.raises(ValueError):
        atr_position_size(100_000, 2.0, 3.0, 1.5, 50.0, 0.25)


def test_result_is_integer():
    assert isinstance(atr_position_size(100_000, 1.7, 3.0, 0.01, 33.33, 0.25),
                      int)
