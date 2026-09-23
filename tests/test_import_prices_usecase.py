"""Unit tests for ImportPricesUseCase retry and partial-failure behavior."""

import unittest
from datetime import date

from mrmkt.common.sql import Duplicate
from mrmkt.entity.stock_price import StockPrice
from mrmkt.usecase.import_prices import ImportPricesResult, ImportPricesUseCase


def _bar(symbol, day="2024-01-02"):
    return StockPrice(
        symbol=symbol,
        date=date.fromisoformat(day),
        open=100.0,
        high=105.0,
        low=99.0,
        close=104.0,
        volume=1000.0,
    )


class ScriptedPriceSource:
    """Fake price source with scripted failures before succeeding."""

    def __init__(self, bars, failures_before_success=0, always_fail=()):
        self.bars = bars
        self.failures_before_success = failures_before_success
        self.always_fail = set(always_fail)
        self.calls = []

    def get_prices(self, symbols, start, end):
        self.calls.append(list(symbols))
        if self.always_fail.intersection(symbols):
            raise RuntimeError("market data unavailable")
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise RuntimeError("transient outage")
        return {symbol: [self.bars[symbol]] for symbol in symbols if symbol in self.bars}


class RecordingPriceDestination:
    """Fake destination that records bars and rejects duplicates."""

    def __init__(self):
        self.stored = {}

    def add_price(self, price):
        key = (price.symbol, price.date)
        if key in self.stored:
            raise Duplicate("already stored")
        self.stored[key] = price


class TestImportPricesUseCase(unittest.TestCase):
    def setUp(self):
        self.start = date(2024, 1, 1)
        self.end = date(2024, 1, 31)
        self.delays = []
        self.progress = []

    def make_usecase(self, source, dest, **kwargs):
        kwargs.setdefault("sleep", self.delays.append)
        kwargs.setdefault("on_progress", lambda done, total: self.progress.append((done, total)))
        return ImportPricesUseCase(source, dest, **kwargs)

    def test_retries_transient_failure_then_succeeds(self):
        source = ScriptedPriceSource({"AAPL": _bar("AAPL")}, failures_before_success=2)
        dest = RecordingPriceDestination()
        usecase = self.make_usecase(source, dest)

        result = usecase.execute(["AAPL"], self.start, self.end)

        self.assertEqual(result.imported, 1)
        self.assertEqual(result.failed_batches, [])
        self.assertEqual(len(source.calls), 3)
        self.assertEqual(self.delays, [1.0, 2.0])
        self.assertEqual(self.progress, [(1, 1)])

    def test_persistent_failure_isolates_batch_and_continues(self):
        source = ScriptedPriceSource(
            {"AAPL": _bar("AAPL"), "MSFT": _bar("MSFT")},
            always_fail={"AAPL"},
        )
        dest = RecordingPriceDestination()
        usecase = self.make_usecase(source, dest)
        usecase.batch_size = 1

        result = usecase.execute(["AAPL", "MSFT"], self.start, self.end)

        self.assertEqual(result.imported, 1)
        self.assertEqual(result.failed_batches, [["AAPL"]])
        self.assertEqual(result.failed_symbols, ["AAPL"])
        self.assertIn(("MSFT", date(2024, 1, 2)), dest.stored)
        self.assertEqual(self.progress, [(1, 2), (2, 2)])

    def test_duplicates_are_skipped_not_counted(self):
        dest = RecordingPriceDestination()
        dest.add_price(_bar("AAPL"))
        source = ScriptedPriceSource({"AAPL": _bar("AAPL")})
        usecase = self.make_usecase(source, dest)

        result = usecase.execute(["AAPL"], self.start, self.end)

        self.assertIsInstance(result, ImportPricesResult)
        self.assertEqual(result.imported, 0)
        self.assertEqual(result.failed_batches, [])

    def test_inverted_range_fails_before_any_request(self):
        source = ScriptedPriceSource({})
        dest = RecordingPriceDestination()
        usecase = self.make_usecase(source, dest)

        with self.assertRaises(ValueError):
            usecase.execute(["AAPL"], self.end, self.start)

        self.assertEqual(source.calls, [])
