"""Unit tests for --strategy-file plugin loading (registry execution)."""

import pytest
from hamcrest import assert_that, contains_string, equal_to

from mrmkt.backtest.strategy import STRATEGIES, build_strategy, load_strategy_file


def _write_module(tmp_path, name, body):
    path = tmp_path / f"{name}.py"
    path.write_text(body)
    return str(path)


def _dummy_source(strategy_name, param_default=5):
    return (
        "import pandas as pd\n"
        "from mrmkt.backtest.strategy import Strategy, register\n"
        "from mrmkt.backtest.strategy.base import MarketContext, ParamSpec, SignalSet\n"
        f"@register({strategy_name!r})\n"
        "class FileStrategy(Strategy):\n"
        "    def __init__(self, size=5):\n"
        "        self.size = size\n"
        "    @classmethod\n"
        "    def param_specs(cls):\n"
        "        return {'size': ParamSpec(int, 5, 'test param')}\n"
        "    def generate(self, close, high, low, context=None):\n"
        "        entries = pd.DataFrame(False, index=close.index, columns=close.columns)\n"
        "        exits = pd.DataFrame(False, index=close.index, columns=close.columns)\n"
        "        entries.iloc[350, :] = True\n"
        "        exits.iloc[355, :] = True\n"
        "        return SignalSet(entries, exits)\n"
        "    def describe(self):\n"
        "        return 'file-loaded test strategy'\n"
    )


def test_loads_file_and_registers_strategy(tmp_path):
    path = _write_module(tmp_path, "plug_a", _dummy_source("file-alpha"))

    assert_that(load_strategy_file(path), equal_to(["file-alpha"]))

    strategy = build_strategy("file-alpha", {"size": "7"})
    assert_that(strategy.size, equal_to(7))  # type: ignore[attr-defined]
    assert_that("file-alpha" in STRATEGIES, equal_to(True))


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(ValueError) as ctx:
        load_strategy_file(str(tmp_path / "absent.py"))

    assert_that(str(ctx.value), contains_string("not found"))


def test_file_without_registrations_is_rejected(tmp_path):
    path = _write_module(tmp_path, "plug_empty", "VALUE = 42\n")

    with pytest.raises(ValueError) as ctx:
        load_strategy_file(path)

    assert_that(str(ctx.value), contains_string("registered no strategies"))


def test_duplicate_name_is_rejected_without_clobbering(tmp_path):
    first = _write_module(tmp_path, "plug_b1", _dummy_source("file-beta"))
    second = _write_module(tmp_path, "plug_b2", _dummy_source("file-beta"))
    load_strategy_file(first)

    with pytest.raises(ValueError) as ctx:
        load_strategy_file(second)

    assert_that(str(ctx.value), contains_string("already registered"))


def test_broken_file_reports_import_failure(tmp_path):
    path = _write_module(tmp_path, "plug_broken", "raise RuntimeError('boom')\n")

    with pytest.raises(ValueError) as ctx:
        load_strategy_file(path)

    assert_that(str(ctx.value), contains_string("failed to import"))


def test_partial_registration_rolls_back_on_failure(tmp_path):
    body = (
        "from mrmkt.backtest.strategy import register\n"
        "from mrmkt.backtest.strategy.buy_red import BuyRedStrategy\n"
        "register('plugin-partial-failure-review')(BuyRedStrategy)\n"
        "raise RuntimeError('boom after registering')\n"
    )
    path = _write_module(tmp_path, "plug_partial", body)

    with pytest.raises(ValueError, match="failed to import"):
        load_strategy_file(path)

    assert_that("plugin-partial-failure-review" in STRATEGIES, equal_to(False))
    with pytest.raises(ValueError, match="unknown strategy"):
        build_strategy("plugin-partial-failure-review", {})
