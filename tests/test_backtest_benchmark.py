"""Unit tests for benchmark/tradable symbol splitting in backtest run."""

import unittest

from hamcrest import assert_that, equal_to, none

from mrmkt.cli import split_benchmark_symbol


class TestSplitBenchmarkSymbol(unittest.TestCase):
    def test_no_benchmark_leaves_selection(self):
        tradables, note = split_benchmark_symbol(["AAPL", "MSFT"], "")

        assert_that(tradables, equal_to(["AAPL", "MSFT"]))
        assert_that(note, none())

    def test_unselected_benchmark_leaves_selection(self):
        tradables, note = split_benchmark_symbol(["AAPL", "MSFT"], "SPY")

        assert_that(tradables, equal_to(["AAPL", "MSFT"]))
        assert_that(note, none())

    def test_benchmark_excluded_among_others(self):
        tradables, note = split_benchmark_symbol(["SPY", "AAPL"], "SPY")

        assert_that(tradables, equal_to(["AAPL"]))
        assert_that("excluded" in (note or ""), equal_to(True))

    def test_sole_benchmark_symbol_stays_tradable(self):
        tradables, note = split_benchmark_symbol(["SPY"], "SPY")

        assert_that(tradables, equal_to(["SPY"]))
        assert_that(note is not None, equal_to(True))
