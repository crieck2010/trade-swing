# trade-swing

One reference swing-trend strategy run through the full validation loop:
**strategy → cost-aware backtest → overfit gates → verdict report.**

The strategy is a long/flat trend-follower (fast/slow moving-average
cross + ATR trailing stop, ATR position sizing, continuous regime
conviction as an entry gate). The point of the repo is not the strategy
— it is the pipeline. A demo PASS here proves the *validation
machinery* works: the same backtest, the same cost model, the same
gates, and the same report schema that a real strategy candidate will
face. A demo PASS says nothing about profitability.

Part of the [trade-suite](https://github.com/crieck2010/trade-suite)
algorithmic trading system. It consumes `trade-backtest` (execution +
accounting) and `trade-overfit` (gate statistics), gates entries with
`trade-regime` conviction when available, and hands verdicts to
`trade-agents` / `trade-paper`.

## Install

```bash
pip install trade-swing
# or from source (no install needed for tests)
git clone https://github.com/crieck2010/trade-swing
cd trade-swing
PYTHONPATH=src pytest
```

Requires Python 3.10+. Stdlib only — no third-party dependencies.
Sibling packages (`trade-backtest`, `trade-overfit`, `trade-regime`)
are optional and imported lazily; everything degrades loudly, never
silently, when they are missing.

## Quick start

```python
from trade_swing.demo import demo_bars, BASKETS
from trade_swing.strategy import SwingConfig
from trade_swing.backtest import run_backtest
from trade_swing.validate import run_validation
from trade_swing.report import build_report, report_to_json

bars = demo_bars(seed=7)
sub = {s: bars[s] for s in BASKETS["trend"]}

bt = run_backtest(sub, config=SwingConfig())          # cost-aware backtest
val = run_validation(bt)                              # overfit gates
report = build_report(bt, val)                        # schema_version 1
print(report["validation"]["status"])                 # PASS
print(report_to_json(report)[:200])
```

CLI:

```bash
trade-swing demo                        # trend vs chop discrimination check
trade-swing validate --basket trend     # backtest + gates + verdict table
trade-swing backtest --basket chop --json
trade-swing signals --basket trend      # recent non-flat signals per symbol
trade-swing report --basket trend        # full JSON validation report
trade-swing presets                     # conservative / balanced / aggressive
```

See `examples/swing_example.py` for the full walkthrough.

## The maths

**What you learn.** How a complete strategy-validation loop is built:
how trend signals are defined without look-ahead, how position size
follows volatility instead of conviction, how costs compound against an
edge, and — the part most backtests skip — how to ask whether the
result is skill or the best-looking accident among many tried.

**Why it matters.** A backtest is a claim about the future disguised as
a fact about the past. The industry's standard failure mode is not a
bad strategy but a good-looking backtest: parameters tuned until the
equity curve smiles, costs assumed away, one lucky path mistaken for an
edge. The gates in this repo exist to make that failure mode *loud*.
Deflated Sharpe asks "how impressive is this Sharpe given how many
things I could have tried"; walk-forward asks "did it work on data the
parameters never saw"; regime conditioning asks "does it only work when
the market cooperates". A strategy that cannot pass these on real data
does not deserve capital — and this repo is where you learn to run them.

**The maths.** Each implemented from scratch (stdlib only):

- *MA crossover.* Fast SMA(n_f) and slow SMA(n_s), SMA_n(t) = (1/n)·Σ_{i=0}^{n−1} C_{t−i}.
  Enter long when the fast crosses *above* the slow
  (F_t > S_t and F_{t−1} ≤ S_{t−1}); exit when it crosses back under.
  The cross is a low-pass-filter duel: the fast average reacts to new
  information sooner, so their ordering estimates the sign of the local
  trend. Every signal uses only closes ≤ t — no look-ahead, verified by
  test.
- *Wilder ATR.* True range TR_t = max(H−L, |H−C_{t−1}|, |L−C_{t−1}|);
  ATR is Wilder's smoothed mean: ATR_t = (ATR_{t−1}·(n−1) + TR_t)/n,
  seeded with the plain mean of the first n TRs. It measures "a normal
  day's move" in price units, including overnight gaps — which is why
  the stop and the sizer are denominated in it.
- *ATR position sizing.* shares = ⌊(equity × risk) / (ATR × stop_multiple)⌋,
  capped so position value ≤ 25% of equity. If the stop is hit, the
  loss is ≈ risk% of equity *by construction* — size adapts to
  volatility instead of the trader's mood. A $5 stock with a $2 ATR
  gets a smaller position than a $500 stock with a $2 ATR, automatically.
- *Sharpe and deflated Sharpe.* Sharpe = √252 · mean(r)/sd(r): excess
  return per unit of realized wobble. But the Sharpe you *report* is the
  maximum over everything you tried, and maxima are biased upward.
  Deflated Sharpe (Bailey & López de Prado 2014) corrects for selection
  bias under multiple testing: it asks for the probability the true
  Sharpe exceeds a benchmark given the number of trials — here N=1,
  since the reference parameters were fixed, not tuned.
- *Walk-forward validation.* Fit on a trailing window, trade the next
  window out-of-sample, roll forward. The gate takes the *median*
  out-of-sample Sharpe across windows: a strategy whose edge lives in
  one lucky sub-period fails even if its full-sample Sharpe shines.
- *Regime conditioning.* The worst-regime Sharpe must clear zero: an
  edge that only exists in bull markets is a bull-market bet, not a
  strategy. (Regime labels here come from `trade-overfit`'s
  volatility/trend partition; live, `trade-regime` conviction gates new
  entries — it can veto entries, never force or block exits.)

Full derivations, assumptions, and the cost model: `docs/METHODOLOGY.md`.

## Interop

| Sibling | Adapter |
|---|---|
| trade-backtest | primary backtest engine (lazy; signal intents → `Signal`, sizing → `PositionSizer`) |
| trade-overfit | gate statistics: DSR, walk-forward, regime report, gate presets |
| trade-regime | conviction dict → entry gate (`regime_min_conviction`) |
| trade-data-equities | real bars in, same pipeline out (see `docs/VALIDATION.md`) |
| trade-agents / trade-paper | validation report → researcher input / paper candidate |

Trigger logic lives only in `strategy.py`; both backtest engines
consume the same intent stream, so they cannot disagree on *what* was
signaled — only on accounting, which the report flags via the
`engine` field (`"trade-backtest"` vs `"internal-fallback"`).

All sibling imports are lazy — trade-swing imports and tests clean with
nothing else installed. Missing `trade-overfit` turns every gate
`SKIPPED` (loud); missing `trade-backtest` falls back to the internal
event loop (loud).

## Honest limitations

- A demo PASS proves the validation pipeline works, **not** that the
  strategy is profitable. Demo bars are seeded random walks.
- Trend systems bleed in chop — the chop basket exists to show the
  gates catching exactly that (Sharpe −1.08, three gates FAIL).
- Parameters (20/50/ATR14, 3× stop, 1% risk) are conventions, not
  optimized values. Tuning them on the demo until it passes would *be*
  overfitting.
- Synthetic bars omit real gaps, microstructure, corporate actions,
  liquidity constraints, and actual fills.
- Costs are assumptions ($0.005/share, 5 bps slippage, 2 bps spread),
  not observed execution. Cost drag is reported, not hidden.
- Stops trigger at bar close and fill at the next open — a one-bar
  simplification, identical in both engines.
- Long/flat only: no shorts, no leverage, no intraday logic.
- Past (or demo) performance does not predict future results.

## Docs

- `docs/ARCHITECTURE.md` — module map and design decisions
- `docs/METHODOLOGY.md` — strategy math, cost model, gate definitions
- `docs/VALIDATION.md` — real-data runbook (`trade-data-equities` +
  `PolygonProvider`); what PASS does and does not mean
- `examples/swing_example.py` — end-to-end walkthrough
- `CHANGELOG.md` — release history

## License

MIT. See `LICENSE`.
