# METHODOLOGY

The math behind the reference strategy, the cost model, the gates, and
the demo calibration. Nothing here is novel — it is all standard
material, implemented from scratch so there are no hidden dependencies
and every assumption is visible.

## 1. Trend signal: MA crossover

Definitions on closes C_t:

- SMA_n(t) = (1/n) · Σ_{i=0}^{n−1} C_{t−i}
- Enter long at t iff F_t > S_t **and** F_{t−1} ≤ S_{t−1}
  (F = fast SMA(20), S = slow SMA(50) by default)
- Exit at t iff F_t < S_t **and** F_{t−1} ≥ S_{t−1}, or the trailing
  stop triggers (below).

Intuition: each SMA is a low-pass filter; the fast one has less lag, so
the *ordering* of the two estimates the sign of the local trend while
rejecting day-to-day noise. The crossover is late by construction —
that lag is the price of the noise rejection, and it is why trend
systems give back the start of every move and the end of every move.
Every quantity used at bar t depends only on closes ≤ t (tested by
`test_no_lookahead`).

## 2. Volatility: Wilder ATR

True range captures the full daily excursion including gaps:

- TR_t = max(H_t − L_t, |H_t − C_{t−1}|, |L_t − C_{t−1}|)

Wilder's ATR smooths it with a slowly-adapting mean:

- ATR_t = (ATR_{t−1}·(n−1) + TR_t) / n, n = 14,
  seeded with the plain mean of the first n true ranges.

ATR is denominated in *price units per normal day*. Both the stop
distance and the position size are expressed in ATRs, so a volatile
$20 stock and a calm $500 stock are treated in comparable risk units.

## 3. Trailing stop and re-entry

- While long: stop_t = max(stop_{t−1}, C_t − m·ATR_t), m = 3.
  The stop ratchets up behind rising prices and never moves down.
- Exit at t iff C_t < stop_t (stop trigger, evaluated at bar close,
  filled at the next open — a documented one-bar simplification).
- **Re-entry rule:** a stop-out while F_t > S_t (trend intact) freezes
  the stop level; a later close above it re-enters long. A cross-down
  exit clears the reference (the trend broke — wait for a fresh cross).
  Without the re-entry rule, a single noise shake-out can sideline the
  system for an entire trend; with it, the system behaves like a
  stop-and-resume trend follower.

## 4. Position sizing

shares = ⌊ (equity × risk_per_trade) / (ATR × stop_multiple) ⌋,
then capped: shares × price ≤ equity × max_position_pct.

Default risk_per_trade = 1%, max_position_pct = 25%. If the stop is hit,
the realized loss is approximately risk_per_trade of equity *by
construction* — the sizing equation is just the stop equation solved
for quantity. The cap keeps a tiny-ATR instrument from becoming an
outsized portfolio bet.

## 5. Cost model

Per fill (each side):

- cost = qty × (commission_per_share + price × slippage_bps/10⁴
  + price × spread_bps/10⁴ / 2)

Defaults: $0.005/share, 5 bps slippage, 2 bps spread (half charged per
side). Applied post-hoc to every closed round trip, identically for
both backtest engines. The report carries total cost, cost per trade,
and **cost drag** = 1 − net_PnL/gross_PnL: the fraction of the gross
edge consumed by frictions. A WARN fires when drag exceeds 50% — an
edge that lives inside its cost assumptions is not an edge.

## 6. The gates (computed by `trade-overfit`)

| Gate | Asks | Passes iff |
|---|---|---|
| deflated_sharpe | Is the Sharpe impressive given N=1 trial? | DSR ≥ 0.95 |
| oos_sharpe | Median out-of-sample Sharpe across walk-forward windows | ≥ 1.0 |
| max_drawdown | Worst peak-to-trough loss | ≥ −15% (i.e. shallower) |
| regime_stability | Worst-regime Sharpe | > 0 |
| beats_benchmark_net | Ann. return minus equal-weight buy-and-hold, net of costs | > 0 |

- *Deflated Sharpe* (Bailey & López de Prado 2014): the Sharpe you
  report is a maximum over trials; maxima are upward-biased. DSR
  estimates P(true Sharpe > benchmark | trials). Here trials N = 1
  because the reference parameters were fixed, not tuned — the honest
  case.
- *Walk-forward:* train on 252 bars, test on the next 63, roll forward;
  the gate uses the **median** OOS Sharpe so one lucky window cannot
  carry the verdict.
- *Regime stability:* the strategy's Sharpe in its worst volatility/
  trend partition must clear zero — an edge that vanishes outside bull
  markets is a bull-market bet.
- *Beats benchmark net:* the economic-merit gate. Buy-and-hold is free
  to beat only *after* costs; anything less is an expensive index fund.

Each gate reports value, threshold, and margin (value − threshold with
the sign oriented so PASS ⇔ margin ≥ 0).

## 7. Demo calibration (seed 7, 750 bars, 2023-01-02 → 2025-12-26)

**Trend basket** (must PASS): `TREND_A`, `TREND_B` — GBM with drift
≈ 0.15%/day, vol ≈ 1.1%/day, plus planted −18% to −25% V-corrections;
`CRASH_A` — GBM trend, a −65% crash over 30 days, a slow bleed, a
second −45% crash, then recovery. The left-tail events are what
buy-and-hold absorbs and the trailing stop mostly avoids — the
strategy's only structural advantage over the benchmark.

**Chop basket** (must FAIL/WARN): three mean-reverting AR(1) series
(φ = 0.97, vol 1.5–2%/day). No persistent trend exists to follow; the
system whipsaws and the gates catch it.

Result on the reference seed: trend **PASS** (Sharpe 1.91, DD −4.6%,
+1.4%/yr net vs benchmark, 56 trades); chop **FAIL** (Sharpe −1.08,
three gates fail, sample-size WARN). The demo proves the *gates
discriminate* — it is not evidence the strategy makes money.

## 8. What is *not* modeled

Overnight gaps beyond TR's reach are approximated, not replayed
tick-by-tick; corporate actions, dividends, borrow costs, and liquidity
limits are absent; fills are assumed at the printed open in full size;
the benchmark is cost-free buy-and-hold. See VALIDATION.md for the
real-data runbook and README for the full limitations list.
