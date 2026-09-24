"""Cost model: hand-worked one-side and round-trip math.

apply_costs returns (adjusted_trades, summary); summary["cost_drag"] is
1 - net/gross (None when gross <= 0).
"""

import pytest

from trade_swing.costs import CostModel, apply_costs


def test_one_side_hand_computed():
    m = CostModel()
    # qty 100 @ 50: commission 0.50 + slippage 2.50 + half-spread 0.50
    assert m.one_side(100, 50.0) == pytest.approx(3.50)


def test_round_trip_hand_computed():
    m = CostModel()
    # buy 100 @ 50 (3.50) + sell 100 @ 60 (0.50 + 3.00 + 0.60)
    assert m.round_trip(100, 50.0, 60.0) == pytest.approx(3.50 + 4.10)


def test_apply_costs_trade():
    m = CostModel()
    trades = [{"symbol": "T", "quantity": 3, "entry_price": 110.0,
               "exit_price": 130.0, "pnl_gross": 60.0}]
    out, summary = apply_costs(trades, m)
    # commission 0.03 + slippage 0.36 + spread 0.072 = 0.462
    assert out[0]["cost"] == pytest.approx(0.462)
    assert out[0]["pnl_net"] == pytest.approx(59.538)
    assert summary["n_trades"] == 1
    assert summary["total_cost"] == pytest.approx(0.462)


def test_apply_costs_summary():
    m = CostModel()
    trades = [
        {"symbol": "A", "quantity": 1, "entry_price": 10.0,
         "exit_price": 12.0, "pnl_gross": 2.0},
        {"symbol": "B", "quantity": 1, "entry_price": 10.0,
         "exit_price": 9.0, "pnl_gross": -1.0},
    ]
    out, summary = apply_costs(trades, m)
    assert summary["n_trades"] == 2
    assert summary["total_pnl_gross"] == pytest.approx(1.0)
    assert summary["total_pnl_net"] == \
        pytest.approx(summary["total_pnl_gross"] - summary["total_cost"])
    assert summary["cost_drag"] == \
        pytest.approx(1.0 - summary["total_pnl_net"] / 1.0)
    assert summary["cost_drag"] > 0


def test_apply_costs_empty():
    out, summary = apply_costs([], CostModel())
    assert out == [] and summary["n_trades"] == 0
    assert summary["cost_drag"] is None  # gross <= 0 -> undefined


def test_negative_cost_model_raises():
    with pytest.raises(ValueError):
        CostModel(commission_per_share=-0.01)
