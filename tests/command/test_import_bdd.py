"""BDD coverage for ImportPricesUseCase and FetchTickersUseCase, driven directly."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.repo.tickers import ReadOnlyTickerRepository
from mrmkt.command.symbols_import import FetchTickersUseCase
from mrmkt.command.prices_import import ImportPricesUseCase

FEATURE = Path(__file__).parent.parent / "features" / "command" / "import.feature"
scenarios(str(FEATURE))

START = date(2022, 1, 3)


class FakePriceSource:
    def __init__(self, bars_by_symbol, failing=()):
        self.bars_by_symbol = bars_by_symbol
        self.failing = set(failing)

    def get_prices(self, symbols, start, end):
        if ",".join(symbols) in self.failing:
            raise ConnectionError("boom")
        return {
            symbol: [
                bar for bar in self.bars_by_symbol.get(symbol, [])
                if start <= bar.date <= end
            ]
            for symbol in symbols
        }


class FakeTickerSource(ReadOnlyTickerRepository):
    def __init__(self, tickers):
        self.tickers = tickers

    def get_symbols(self):
        return [ticker.ticker for ticker in self.tickers]

    def get_tickers(self):
        return list(self.tickers)


def _bars(symbol, n=5):
    days = []
    current = START
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return [
        StockPrice(
            symbol=symbol, date=day, open=100.0, high=101.0, low=99.0,
            close=100.0, volume=1000.0,
        )
        for day in days
    ]


@pytest.fixture
def import_context():
    return SimpleNamespace(
        local=None, source=None, tickers=None, result=None, error=None,
        start=None, end=None,
    )


@given("a clean price store")
def clean_price_store(import_context):
    import_context.local = InMemoryFinancialRepository()


@given("a clean ticker store")
def clean_ticker_store(import_context):
    import_context.local = InMemoryFinancialRepository()


@given(parsers.parse('a fake price source serving 5 bars for "{symbol}"'))
def price_source_serving(import_context, symbol):
    import_context.source = FakePriceSource({symbol: _bars(symbol)})
    import_context.start = _bars(symbol)[0].date
    import_context.end = _bars(symbol)[-1].date


@given(parsers.parse('a fake price source failing batch "{batch}"'))
def price_source_failing(import_context, batch):
    import_context.source = FakePriceSource({}, failing=[batch])
    import_context.start = START
    import_context.end = START + timedelta(days=10)


@given(parsers.parse('a fake ticker source serving "{first}" and "{second}"'))
def ticker_source_serving(import_context, first, second):
    import_context.tickers = [
        Ticker(ticker=first, exchange="NASDAQ", type="us_equity"),
        Ticker(ticker=second, exchange="NASDAQ", type="us_equity"),
    ]


def _run_import(import_context, symbols):
    use_case = ImportPricesUseCase(
        import_context.source, import_context.local,
        max_attempts=1, sleep=lambda seconds: None,
    )
    try:
        import_context.result = use_case.execute(symbols, import_context.start, import_context.end)
        import_context.error = None
    except ValueError as error:
        import_context.result = None
        import_context.error = str(error)


@when(parsers.parse('I import "{symbols}" for the 5-bar window'))
def run_import(import_context, symbols):
    _run_import(import_context, symbols.split(","))


@when(parsers.parse('I import "{symbols}" for the 5-bar window again'))
def run_import_again(import_context, symbols):
    _run_import(import_context, symbols.split(","))


@when(parsers.parse('I import "{symbols}" for a reversed window'))
def run_import_reversed(import_context, symbols):
    import_context.start, import_context.end = import_context.end, import_context.start
    _run_import(import_context, symbols.split(","))


@when("I fetch tickers")
def run_fetch(import_context):
    use_case = FetchTickersUseCase(FakeTickerSource(import_context.tickers), import_context.local)
    import_context.result = use_case.execute()


@when("I fetch tickers again")
def run_fetch_again(import_context):
    use_case = FetchTickersUseCase(FakeTickerSource(import_context.tickers), import_context.local)
    import_context.result = use_case.execute()


@then(parsers.parse("{count:d} bars are stored for \"{symbol}\""))
def bars_stored(import_context, count, symbol):
    assert len(import_context.local.list_prices(symbol)) == count


@then(parsers.parse('the batch "{batch}" is recorded failed'))
def batch_failed(import_context, batch):
    assert [batch.split(",")] == import_context.result.failed_batches


@then("the import fails naming the date order")
def import_rejected(import_context):
    assert import_context.result is None
    assert "--from must be on or before --to" in import_context.error


@then(parsers.parse("{count:d} tickers are imported"))
def tickers_imported(import_context, count):
    assert import_context.result == count
