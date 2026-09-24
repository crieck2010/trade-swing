# VALIDATION

How to run the full loop on **real data**, and what the verdict means
when you do. The demo (`trade-swing demo`) proves the pipeline runs;
this page is about proving something about a *strategy*.

## Real-data runbook

The pipeline accepts any bars shaped like
`{date, open, high, low, close, volume}` with ISO dates. Pull them from
`trade-data-equities` and everything downstream is unchanged:

```python
from datetime import date
from trade_data_equities.providers.polygon import PolygonProvider
from trade_data_equities.models import Symbol, Timeframe
from trade_data_equities.adjustments import adjust_bars

from trade_swing.strategy import SwingConfig
from trade_swing.backtest import run_backtest
from trade_swing.validate import run_validation
from trade_swing.report import build_report, report_to_json

provider = PolygonProvider()  # reads POLYGON_API_KEY; never log it
symbols = ["AAPL", "MSFT", "NVDA"]
start, end = date(2018, 1, 1), date(2026, 1, 1)

bars_by_symbol = {}
for ticker in symbols:
    raw = provider.get_bars(Symbol(ticker), Timeframe.DAY, start, end)
    adj = adjust_bars(raw)  # splits + dividends; unadjusted degrades loudly
    bars_by_symbol[ticker] = [
        {"date": b.timestamp.date().isoformat(), "open": b.open,
         "high": b.high, "low": b.low, "close": b.close,
         "volume": b.volume}
        for b in adj
    ]

provenance = {"source": "trade-data-equities/PolygonProvider",
              "symbols": symbols, "start": str(start), "end": str(end),
              "adjusted": True, "delay": "per your Polygon tier"}

bt = run_backtest(bars_by_symbol, config=SwingConfig(),
                  provenance=provenance)
val = run_validation(bt)  # benchmark arg omitted -> that gate SKIPPED
report = build_report(bt, val, provenance)
print(report_to_json(report))
```

Notes for honest runs:

- **Adjust for splits and dividends.** Unadjusted prices create fake
  −90% crashes that the trailing stop "dodges" — free fake alpha.
  `adjust_bars` exists for exactly this.
- **Mind the delay.** Free-tier Polygon data is end-of-day delayed;
  record the tier in provenance. A strategy validated on delayed data
  and traded on real-time data is a different strategy.
- **Align calendars.** Drop symbols/dates with missing bars or align
  explicitly and say so in provenance — silent forward-fill is
  look-ahead's quiet cousin.
- **Provide a benchmark.** `run_validation(bt,
  benchmark_returns=[...])` needs per-bar benchmark returns aligned to
  the equity curve (e.g. SPY total-return series over the same dates).
  Omit it and the economic-merit gate reports SKIPPED instead of
  guessing.
- **Costs are still assumptions.** Consider widening slippage for less
  liquid names and documenting why.

## What PASS means (and does not)

A PASS on real data means: *under these costs, on this history, the
strategy's risk-adjusted return survives a multiple-testing correction,
holds up out-of-sample across walk-forward windows, is not confined to
one market regime, and beats buy-and-hold net of costs.* That is a
meaningful filter — most published backtests fail at least one gate —
but it is not a promise:

- **It is still in-sample in the deepest sense.** You chose the
  strategy family, the universe, and the date range. The gates correct
  for parameter trials, not for *researcher* degrees of freedom.
- **Regimes change.** A worst-regime Sharpe above zero on 2018–2026
  says nothing about a regime that has not occurred yet.
- **Costs are modeled, fills are assumed.** Real slippage, partial
  fills, and corporate-action edge cases only appear in paper trading.
- **One PASS is a ticket to paper trading, not to capital.** The
  suite's sequence is: gates → `trade-paper` incubation (one quarter,
  regime filter active) → review → capital. A PASS that decays in paper
  trading was luck wearing a lab coat.

## What FAIL / WARN means

- **FAIL on any gate:** do not trade it. Read the margin — a Sharpe
  gate failing by 0.02 is a different conversation than failing by 2.0.
- **WARN (sample size / cost drag / concentration):** the verdict is
  provisional even if the gates pass. Thirty trades is a *minimum*;
  prefer hundreds before taking a PASS seriously.
- **SKIPPED:** the verdict is "unknown", not "pass". Missing
  `trade-overfit` or a missing benchmark both land here, loudly.

## The one rule

Never tune the strategy on the data you validate it on and then report
the validation as evidence. If you change a parameter, the previous
validation is void — re-run from scratch. The demo exists so you can
practice the loop somewhere the stakes are zero.
