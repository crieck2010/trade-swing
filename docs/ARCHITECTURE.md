# ARCHITECTURE

`trade-swing` v0.1.0 — one reference swing-trend strategy through the
complete validation loop.

## What this repo is

Not a strategy product. A **validation-loop reference implementation**:
the smallest thing that exercises strategy → cost-aware backtest →
overfit gates → verdict report end to end, so every future strategy
candidate reuses the same machinery and the same report schema. The
strategy itself (long/flat MA-cross + ATR trailing stop) is deliberately
ordinary — it is the control group, not the discovery.

## Module map

```
src/trade_swing/
├── strategy.py    # the single source of truth for trigger logic
│                  # SwingConfig, pure indicators (SMA, Wilder TR/ATR),
│                  # _SignalWalk: cross + trailing-stop + re-entry rule,
│                  # regime-conviction entry gate. No look-ahead by construction.
├── sizing.py      # atr_position_size: floor((E*risk)/(ATR*mult)), capped
├── costs.py       # CostModel ($/share + bps slippage + half-spread);
│                  # apply_costs attaches cost/pnl_net to closed trades
├── metrics.py     # stdlib headline stats on equity curves / trade lists
├── backtest.py    # DUAL PATH: trade-backtest (primary, lazy) or the
│                  # internal event loop (fallback, loud). Both consume the
│                  # intent stream from strategy.py; fills at next open.
├── validate.py    # lazy adapter to trade-overfit: 5 gates + 3 WARN checks.
│                  # Missing sibling -> every gate SKIPPED, never approximated.
├── report.py      # ValidationReport, schema_version 1, JSON-serializable
├── demo.py        # seeded synthetic bars: trend basket (PASS) + chop basket
│                  # (FAIL/WARN). Proves the pipeline, not the strategy.
├── presets.py     # conservative / balanced / aggressive starting points
├── cli.py         # signals, backtest, validate, report, demo, presets,
│                  # license, update-check
└── licensing.py   # license-key hook (stub) + update check
```

## Key design decisions

**1. Trigger logic lives in exactly one place (`strategy.py`).**
Both backtest engines consume the signal-intent stream (`enter_long` /
`exit_long` / `flat`) produced by `_SignalWalk`. The engines differ only
in cash accounting — they cannot disagree on *what* was signaled. The
report's `engine` field records which one ran.

**2. Signals at close, fills at next open.**
The strategy decides on bar t's close; the engines fill at bar t+1's
open. This is the standard no-look-ahead execution model and is tested
explicitly. Stops are *triggered* at bar close (a documented one-bar
simplification) and filled at the next open, identically in both paths.

**3. Stop-out re-entry rule.**
A stop-out while the trend is intact (fast still above slow) does not
require a fresh MA cross to re-enter — price recovering above the frozen
stop level re-enters. Without this, one noise shake-out sidelines the
system for the rest of a trend (observed: 19% in-market on a clean bull
run). A cross-down exit clears the re-entry reference (trend broken;
wait for a genuinely new cross). Regime conviction can veto *entries*
only — never exits.

**4. Costs are post-hoc and identical across engines.**
`apply_costs` runs on closed round trips after the backtest, so both
engines report under identical cost assumptions. The report carries the
model parameters and the cost-drag summary — costs are evidence, not a
footnote.

**5. Gates are computed by `trade-overfit`, never reimplemented.**
`validate.py` is a thin adapter: it builds the evidence dict (DSR,
walk-forward median OOS Sharpe, max drawdown, worst-regime Sharpe,
net excess vs benchmark) and maps `trade-overfit`'s preset gates to
per-gate verdicts with value/threshold/margin. If the sibling is
missing, every gate is `SKIPPED` and the overall verdict is `SKIPPED` —
a loud "this proves nothing", never a silent approximation.

**6. The WARN layer is ours.**
Three honesty checks sit *above* the gates: fewer than 30 trades,
cost drag above 50% of gross P&L, one trade above 50% of absolute P&L.
A gate can PASS on a result that is still untrustworthy; the WARNs say
so out loud.

**7. The demo is calibrated, and the calibration is documented.**
The trend basket is engineered so the reference strategy passes all
five gates (persistent trends + planted left-tail events the trailing
stop mostly avoids); the chop basket is engineered so it fails
(mean-reverting noise the system whipsaws on). The demo's job is to
show both verdict paths, deterministically (seed 7). See METHODOLOGY
for the exact construction and VALIDATION for why demo PASS ≠ real PASS.

## Data flow

```
demo bars (or real bars from trade-data-*)
        │
        ▼
strategy.generate_signals  ── intent stream (date, signal, stop, ...)
        │
        ├──► trade-backtest engine ──┐
        │                            ├──► trades + equity curve
        └──► internal event loop ────┘
                        │
                        ▼
              apply_costs (CostModel)
                        │
                        ▼
              validate (trade-overfit gates + WARNs)
                        │
                        ▼
              build_report → ValidationReport (schema v1, JSON)
```

## Scaling & interop notes

- Everything is plain data (dicts/lists) across boundaries — no engine
  objects leak into reports. Any strategy that can emit the intent
  stream can reuse `backtest`/`validate`/`report` unchanged.
- `trade-regime` conviction plugs in as `convictions={date: 0-100}`;
  the strategy treats it as an entry veto only.
- For multi-strategy portfolios, run one report per strategy and let
  the PM layer (`trade-agents`) allocate — this repo never nets
  positions across strategies.
- The internal fallback loop is O(bars × symbols) and dependency-free;
  the primary path delegates scaling to `trade-backtest`.
