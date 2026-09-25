"""BDD coverage for ImportPrices and ImportSymbols, driven directly."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, contains_string, equal_to, none
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.command.import_prices import ImportPrices
from mrmkt.command.import_symbols import ImportSymbols, ImportSymbolsRequest
from mrmkt.common.clock import ClockStub
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.repo.tickers import ReadOnlyTickerRepository

FEATURE = Path(__file__).parent.parent / "features" / "command" / "import.feature"
scenarios(str(FEATURE))

START = date(2022, 1, 3)


class FakePriceSource:
    def __init__(self, bars_by_symbol=None, failing=(), flaky=None):
        self.bars_by_symbol = dict(bars_by_symbol or {})
        self.failing = set(failing)
        self.flaky = dict(flaky or {})
        self.calls = []

    def get_prices(self, symbols, start, end):
        key = ",".join(symbols)
        self.calls.append(list(symbols))
        if key in self.failing:
            raise ConnectionError("boom")
        if self.flaky.get(key, 0) > 0:
            self.flaky[key] -= 1
            raise ConnectionError("transient outage")
        return {
            symbol: [
                bar
                for bar in self.bars_by_symbol.get(symbol, [])
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
            symbol=symbol,
            date=day,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1000.0,
        )
        for day in days
    ]


@pytest.fixture
def import_context():
    return SimpleNamespace(
        local=None,
        source=None,
        tickers=None,
        result=None,
        error=None,
        start=None,
        end=None,
        delays=None,
        progress=None,
        batch_size=None,
    )


def _price_source(import_context):
    if import_context.source is None:
        import_context.source = FakePriceSource()
        import_context.start = START
        import_context.end = START + timedelta(days=10)
    return import_context.source


@given("a clean price store")
def clean_price_store(import_context):
    import_context.local = InMemoryFinancialRepository()


@given("a clean ticker store")
def clean_ticker_store(import_context):
    import_context.local = InMemoryFinancialRepository()


@given(parsers.parse('a fake price source serving 5 bars for "{symbol}"'))
def price_source_serving(import_context, symbol):
    _price_source(import_context).bars_by_symbol[symbol] = _bars(symbol)
    import_context.start = _bars(symbol)[0].date
    import_context.end = _bars(symbol)[-1].date


@given(
    parsers.parse(
        'a fake price source serving 5 bars each for "{first}" and "{second}"'
    )
)
def price_source_serving_two(import_context, first, second):
    source = _price_source(import_context)
    source.bars_by_symbol[first] = _bars(first)
    source.bars_by_symbol[second] = _bars(second)
    import_context.start = _bars(first)[0].date
    import_context.end = _bars(first)[-1].date


@given(parsers.parse('a fake price source failing batch "{batch}"'))
def price_source_failing(import_context, batch):
    _price_source(import_context).failing.add(batch)


@given(parsers.parse('batch "{batch}" fails {count:d} times before succeeding'))
def price_source_flaky(import_context, batch, count):
    _price_source(import_context).flaky[batch] = count


@given(parsers.parse("the import batch size is {size:d}"))
def import_batch_size(import_context, size):
    import_context.batch_size = size


@given(parsers.parse('a fake ticker source serving "{first}" and "{second}"'))
def ticker_source_serving(import_context, first, second):
    import_context.tickers = [
        Ticker(ticker=first, exchange="NASDAQ", type="us_equity"),
        Ticker(ticker=second, exchange="NASDAQ", type="us_equity"),
    ]


def _run_import(import_context, symbols):
    clock = ClockStub()
    clock.set_time(import_context.end)
    import_context.delays = []
    import_context.progress = []
    command = ImportPrices(
        import_context.source,
        import_context.local,
        clock,
        sleep=import_context.delays.append,
        on_progress=lambda done, total: import_context.progress.append((done, total)),
    )
    if import_context.batch_size is not None:
        command.batch_size = import_context.batch_size
    try:
        outcome = command.execute(
            provider="alpaca",
            symbols=symbols,
            all_symbols=False,
            tag=None,
            from_date=import_context.start.isoformat(),
            to_date=import_context.end.isoformat(),
        )
        import_context.result = outcome.result
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
    command = ImportSymbols(
        FakeTickerSource(import_context.tickers), import_context.local
    )
    import_context.result = command.execute(ImportSymbolsRequest(provider="alpaca"))


@when("I fetch tickers again")
def run_fetch_again(import_context):
    command = ImportSymbols(
        FakeTickerSource(import_context.tickers), import_context.local
    )
    import_context.result = command.execute(ImportSymbolsRequest(provider="alpaca"))


@then(parsers.parse('{count:d} bars are stored for "{symbol}"'))
def bars_stored(import_context, count, symbol):
    assert_that(len(import_context.local.list_prices(symbol)), equal_to(count))


@then(parsers.parse("{count:d} bars were imported"))
def bars_imported(import_context, count):
    assert_that(import_context.result.imported, equal_to(count))


@then(parsers.parse("the price source was called {count:d} times"))
def price_source_called(import_context, count):
    assert_that(len(import_context.source.calls), equal_to(count))


@then("the price source was not called")
def price_source_not_called(import_context):
    assert_that(import_context.source.calls, equal_to([]))


@then("the retry delays were:")
def retry_delays_were(import_context, datatable):
    assert_that(
        [float(row[0]) for row in datatable[1:]], equal_to(import_context.delays)
    )


@then("progress reports were:")
def progress_reports_were(import_context, datatable):
    assert_that(
        [(int(row[0]), int(row[1])) for row in datatable[1:]],
        equal_to(import_context.progress),
    )


@then(parsers.parse('the batch "{batch}" is recorded failed'))
def batch_failed(import_context, batch):
    assert_that([batch.split(",")], equal_to(import_context.result.failed_batches))


@then("the import fails naming the date order")
def import_rejected(import_context):
    assert_that(import_context.result, none())
    assert_that(
        import_context.error, contains_string("--from must be on or before --to")
    )


@then(parsers.parse("{count:d} tickers are imported"))
def tickers_imported(import_context, count):
    assert_that(import_context.result.is_success(), equal_to(True))
    assert_that(import_context.result.result, equal_to(count))
