"""CLI and presets: every command runs, JSON parses, presets load."""

import json

import pytest

from trade_swing.cli import main
from trade_swing.presets import PRESETS, get_preset


def test_presets_load():
    assert set(PRESETS) == {"conservative", "balanced", "aggressive"}
    cfg = get_preset("balanced")["config"]
    assert cfg.fast == 20 and cfg.slow == 50
    assert get_preset("aggressive")["config"].risk_per_trade > \
        get_preset("conservative")["config"].risk_per_trade


def test_preset_unknown_raises():
    with pytest.raises(ValueError):
        get_preset("reckless")


def test_cli_demo(capsys):
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "trend" in out and "chop" in out
    # with siblings: PASS line; bare: loud CANNOT EVALUATE
    assert "PASS" in out or "CANNOT EVALUATE" in out


def test_cli_demo_json(capsys):
    assert main(["demo", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    # with trade-overfit installed: trend PASS, chop FAIL/WARN;
    # bare: both SKIPPED (loud, never silent)
    assert payload["trend"]["status"] in ("PASS", "WARN", "FAIL", "SKIPPED")
    assert payload["chop"]["status"] in ("PASS", "WARN", "FAIL", "SKIPPED")


def test_cli_validate_json(capsys):
    assert main(["validate", "--basket", "trend", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] in ("PASS", "WARN", "FAIL", "SKIPPED")


def test_cli_backtest(capsys):
    assert main(["backtest", "--basket", "chop"]) == 0
    assert "engine" in capsys.readouterr().out


def test_cli_backtest_all_baskets(capsys):
    assert main(["backtest", "--basket", "all"]) == 0
    assert "engine" in capsys.readouterr().out


def test_cli_signals(capsys):
    assert main(["signals", "--basket", "trend"]) == 0
    out = capsys.readouterr().out
    assert "enter_long" in out or "exit_long" in out


def test_cli_report(capsys):
    assert main(["report", "--basket", "trend"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["validation"]["status"] in ("PASS", "WARN", "FAIL", "SKIPPED")


def test_cli_presets(capsys):
    assert main(["presets"]) == 0
    assert "conservative" in capsys.readouterr().out


def test_cli_license(capsys):
    assert main(["license"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
