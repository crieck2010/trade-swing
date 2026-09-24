"""End-to-end walkthrough: demo bars -> signals -> backtest -> gates -> report.

Run from the repo root with the sibling packages importable, e.g.::

    PYTHONPATH=src:../trade-overfit/src:../trade-backtest/src \\
        python examples/swing_example.py
"""

from trade_swing.backtest import run_backtest
from trade_swing.demo import BASKETS, demo_bars, demo_benchmark, run_demo
from trade_swing.report import build_report, report_to_json
from trade_swing.strategy import SwingConfig, generate_signals
from trade_swing.validate import run_validation


def main() -> None:
    # 1. seeded demo bars: a trend basket and a chop basket
    bars = demo_bars(seed=7)
    print(f"demo universe: {sorted(bars)} "
          f"({len(next(iter(bars.values())))} bars each)")

    # 2. raw signals for one symbol: entries, exits, trailing stops
    sigs = generate_signals(bars["TREND_A"], SwingConfig())
    events = [s for s in sigs if s["signal"] != "flat"]
    print(f"\nTREND_A non-flat signals: {len(events)}")
    for s in events[:6]:
        print(f"  {s['date']} {s['signal']:10s} "
              f"close-dependent stop={s['stop'] and round(s['stop'], 2)}")

    # 3. cost-aware backtest of the trend basket, both engine paths
    sub = {s: bars[s] for s in BASKETS["trend"]}
    for force in ("trade-backtest", "internal"):
        try:
            bt = run_backtest(sub, config=SwingConfig(),
                              force_engine=force)
        except ImportError:
            print(f"\nengine path {force!r}: sibling not installed, skipped")
            continue
        m = bt["metrics"]
        print(f"\nengine={bt['engine']:<18s} "
              f"CAGR={m['cagr']:.2%} Sharpe={m['sharpe_ratio']:.2f} "
              f"maxDD={m['max_drawdown']:.2%} trades={len(bt['trades'])} "
              f"cost_drag={bt['costs']['cost_drag']:.1%}")

    # 4. the full loop, both baskets, with gate verdicts
    print("\nvalidation:")
    for basket, report in run_demo(seed=7).items():
        v = report["validation"]
        print(f"  {basket:6s} -> {v['status']}")
        for g in v["gates"]:
            val = (f"{g['value']:.4f}" if isinstance(g["value"], float)
                   else g["value"])
            print(f"    {g['name']:22s} {g['verdict']:4s} "
                  f"(value={val}, margin={g['margin']:+.4f})")
        for w in v["warnings"]:
            print(f"    WARN [{w['name']}]: {w['description'][:80]}...")

    # 5. the verdict document
    bt = run_backtest(sub, config=SwingConfig())
    val = run_validation(
        bt, benchmark_returns=demo_benchmark(sub, BASKETS["trend"]))
    report = build_report(bt, val)
    print(f"\nreport schema_version={report['schema_version']} "
          f"engine={report['backtest']['engine']}")
    print("limitations carried in the report:")
    for line in report["limitations"][:3]:
        print(f"  - {line[:90]}...")
    assert report_to_json(report)  # must be JSON-serializable


if __name__ == "__main__":
    main()
