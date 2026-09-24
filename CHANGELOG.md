# Changelog

## v0.1.0 — 2026-09-24

Initial release: one reference swing-trend strategy through the complete
validation loop (strategy → cost-aware backtest → overfit gates →
verdict report).

- `strategy.py` — long/flat MA(20/50) cross + 3× ATR trailing stop;
  stop-out re-entry rule (frozen stop level re-enters while the trend
  is intact; cross-down clears it); regime-conviction entry veto;
  signals at close, fills at next open, no look-ahead by construction.
  Single source of truth for trigger logic across both backtest engines.
- `sizing.py` — ATR position sizing, 1% risk/trade, 25% position cap
- `costs.py` — CostModel ($0.005/share + 5 bps slippage + half-spread),
  applied post-hoc and identically in both engines; cost-drag reporting
- `backtest.py` — dual path: `trade-backtest` (primary, lazy) or the
  internal event loop (fallback, loud); `engine` flag in every result
- `validate.py` — lazy `trade-overfit` adapter: deflated Sharpe,
  walk-forward median OOS Sharpe, max drawdown, worst-regime Sharpe,
  net excess vs benchmark; per-gate value/threshold/margin; missing
  sibling → every gate SKIPPED, never approximated; 3 WARN checks
  (sample size, cost drag, concentration)
- `report.py` — ValidationReport schema v1, JSON-serializable, with
  explicit limitations
- `demo.py` — seeded synthetic bars: trend basket **PASS** (Sharpe 1.91,
  DD −4.6%, +1.4%/yr net vs benchmark, 56 trades) and chop basket
  **FAIL** (Sharpe −1.08, three gates fail) — proves the gates
  discriminate
- `presets.py` — conservative / balanced / aggressive starting points
- CLI: `signals`, `backtest`, `validate`, `report`, `demo`, `presets`,
  `license`, `update-check`
- Docs: README ("The maths": MA crossover, Wilder ATR, ATR sizing,
  Sharpe/deflated-Sharpe, walk-forward), ARCHITECTURE, METHODOLOGY,
  VALIDATION (real-data runbook with `trade-data-equities` /
  `PolygonProvider`)
- 79 tests, all passing (sibling-path and bare/fallback modes)
