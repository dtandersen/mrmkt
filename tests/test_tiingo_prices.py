"""Unit tests for the Tiingo daily-price adapter plus provider wiring."""

import os
from datetime import UTC, date, datetime
from types import SimpleNamespace

from hamcrest import assert_that, contains_string, equal_to
from tests.fakes import CapturingLog

from mrmkt.command.import_prices import (
    ImportPrices,
    ImportPricesRequest,
)
from mrmkt.common.clock import ClockStub
from mrmkt.common.util import to_date
from mrmkt.entity.stock_price import StockPrice
from mrmkt.ext.alpaca_prices import AlpacaPriceSource
from mrmkt.ext.backend import InMemoryBackend
from mrmkt.ext.tiingo_prices import TIINGO_API_KEY_ENV_VAR, TiingoPriceSource

START = date(2024, 1, 2)
END = date(2024, 1, 3)


class StubResponse:
    def __init__(self, payload=None, error=None):
        self.payload = payload if payload is not None else []
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


class StubHttp:
    """Stub HTTP transport recording requests and serving canned rows."""

    def __init__(self, rows_by_symbol=None, error=None):
        self.rows_by_symbol = dict(rows_by_symbol or {})
        self.error = error
        self.calls = []

    def __call__(self, url, *, params=None, headers=None, timeout=None):
        self.calls.append(
            {"url": url, "params": params, "headers": headers, "timeout": timeout}
        )
        if self.error is not None:
            return StubResponse(error=self.error)
        symbol = url.rsplit("/", 2)[-2]
        return StubResponse(payload=self.rows_by_symbol.get(symbol, []))


def _row(day, **overrides):
    row = {
        "date": f"{day.isoformat()}T00:00:00.000Z",
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 104.0,
        "volume": 1000.0,
        "adjOpen": 101.0,
        "adjHigh": 106.0,
        "adjLow": 98.0,
        "adjClose": 103.0,
    }
    row.update(overrides)
    return row


def _source(http, api_key="test-key", log=None):
    return TiingoPriceSource(api_key=api_key, http_get=http, log=log or CapturingLog())


class StubAlpacaDataClient:
    """Stub Alpaca market-data client serving canned bars per symbol."""

    def __init__(self, bars_by_symbol=None):
        self.bars_by_symbol = dict(bars_by_symbol or {})
        self.requests = []

    def get_stock_bars(self, request):
        self.requests.append(request)
        symbols = request.symbol_or_symbols
        if isinstance(symbols, str):
            symbols = [symbols]
        return SimpleNamespace(
            data={symbol: self.bars_by_symbol.get(symbol, []) for symbol in symbols}
        )


def _alpaca_bar(day):
    return SimpleNamespace(
        timestamp=datetime(day.year, day.month, day.day, tzinfo=UTC),
        open=100.0,
        high=105.0,
        low=99.0,
        close=104.0,
        volume=1000.0,
    )


def test_tiingo_logs_connection_and_subscribed_symbols():
    http = StubHttp({"AAPL": [_row(START)], "MSFT": [_row(START)]})
    log = CapturingLog()

    _source(http, log=log).get_prices(["aapl", "MSFT"], START, START)

    assert_that(
        log.lines,
        equal_to(["Connected to Tiingo prices", "Subscribing to AAPL, MSFT"]),
    )


def test_tiingo_logs_nothing_without_a_subscription():
    log = CapturingLog()
    source = _source(StubHttp(), log=log)

    assert_that(
        source.get_prices([], START, END), equal_to([]) if False else equal_to({})
    )
    try:
        source.get_prices(["AAPL"], END, START)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    assert_that(log.lines, equal_to([]))


def test_alpaca_logs_connection_and_subscribed_symbols():
    log = CapturingLog()
    source = AlpacaPriceSource(
        StubAlpacaDataClient({"AAPL": [_alpaca_bar(START)]}), log
    )

    prices = source.get_prices(["aapl"], START, START)

    assert_that(list(prices), equal_to(["AAPL"]))
    assert_that(len(prices["AAPL"]), equal_to(1))
    assert_that(
        log.lines,
        equal_to(["Connected to Alpaca prices", "Subscribing to AAPL"]),
    )


def test_maps_adjusted_bars_and_sends_key_params():
    http = StubHttp({"AAPL": [_row(START), _row(END)]})
    source = _source(http)

    prices = source.get_prices(["AAPL"], START, END)

    assert_that(
        prices,
        equal_to(
            {
                "AAPL": [
                    StockPrice(
                        symbol="AAPL",
                        date=START,
                        open=101.0,
                        high=106.0,
                        low=98.0,
                        close=103.0,
                        volume=1000.0,
                    ),
                    StockPrice(
                        symbol="AAPL",
                        date=END,
                        open=101.0,
                        high=106.0,
                        low=98.0,
                        close=103.0,
                        volume=1000.0,
                    ),
                ]
            }
        ),
    )
    assert_that(len(http.calls), equal_to(1))
    call = http.calls[0]
    assert_that(
        call["url"], equal_to("https://api.tiingo.com/tiingo/daily/AAPL/prices")
    )
    assert_that(
        call["params"],
        equal_to(
            {"startDate": "2024-01-02", "endDate": "2024-01-03", "format": "json"}
        ),
    )
    assert_that(call["headers"], equal_to({"Authorization": "Token test-key"}))


def test_falls_back_to_raw_ohlc_without_adjusted_fields():
    row = _row(START)
    for key in ("adjOpen", "adjHigh", "adjLow", "adjClose"):
        del row[key]
    source = _source(StubHttp({"AAPL": [row]}))

    prices = source.get_prices(["AAPL"], START, START)

    assert_that(len(prices["AAPL"]), equal_to(1))
    bar = prices["AAPL"][0]
    assert_that(
        (bar.open, bar.high, bar.low, bar.close), equal_to((100.0, 105.0, 99.0, 104.0))
    )


def test_normalizes_and_dedupes_symbols():
    http = StubHttp({"AAPL": [_row(START)]})
    source = _source(http)

    prices = source.get_prices(["aapl", "AAPL"], START, START)

    assert_that(list(prices), equal_to(["AAPL"]))
    assert_that(len(http.calls), equal_to(1))


def test_empty_symbols_make_no_requests():
    http = StubHttp()
    source = _source(http)

    assert_that(source.get_prices([], START, END), equal_to({}))
    assert_that(http.calls, equal_to([]))


def test_reversed_window_is_rejected_before_any_request():
    http = StubHttp()
    source = _source(http)

    try:
        source.get_prices(["AAPL"], END, START)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert_that(
            str(error), contains_string("start date must not be after end date")
        )
    assert_that(http.calls, equal_to([]))


def test_http_failures_propagate_for_import_retry_accounting():
    source = _source(StubHttp(error=ConnectionError("tiingo down")))

    try:
        source.get_prices(["AAPL"], START, END)
        raise AssertionError("expected ConnectionError")
    except ConnectionError as error:
        assert_that(str(error), contains_string("tiingo down"))


def test_missing_api_key_is_rejected_with_a_clear_message():
    saved = os.environ.pop(TIINGO_API_KEY_ENV_VAR, None)
    try:
        try:
            TiingoPriceSource(api_key=None, http_get=StubHttp(), log=CapturingLog())
            raise AssertionError("expected ValueError")
        except ValueError as error:
            assert_that(
                str(error),
                contains_string(f"{TIINGO_API_KEY_ENV_VAR} environment variable"),
            )
    finally:
        if saved is not None:
            os.environ[TIINGO_API_KEY_ENV_VAR] = saved


def test_key_reads_from_environment_when_not_passed():
    saved = os.environ.get(TIINGO_API_KEY_ENV_VAR)
    os.environ[TIINGO_API_KEY_ENV_VAR] = "env-key"
    try:
        source = TiingoPriceSource.from_env(
            CapturingLog(), http_get=StubHttp({"AAPL": [_row(START)]})
        )
        assert_that(source.api_key, equal_to("env-key"))
        assert_that(len(source.get_prices(["AAPL"], START, START)["AAPL"]), equal_to(1))
    finally:
        if saved is None:
            os.environ.pop(TIINGO_API_KEY_ENV_VAR, None)
        else:
            os.environ[TIINGO_API_KEY_ENV_VAR] = saved


def _import_with_provider(provider):
    local = InMemoryBackend()
    clock = ClockStub()
    clock.set_time(END)
    command = ImportPrices(
        _source(StubHttp({"AAA": [_row(START)]})),
        local,
        clock,
        sleep=lambda _: None,
    )
    return command.execute(
        ImportPricesRequest(
            provider=provider,
            symbols=["AAA"],
            all_symbols=False,
            tag=None,
            from_date=to_date("2024-01-02").isoformat(),
            to_date=to_date("2024-01-02").isoformat(),
        )
    )


def test_import_prices_accepts_tiingo_provider():
    outcome = _import_with_provider("tiingo")

    assert_that(outcome.is_success(), equal_to(True))


def test_import_prices_still_rejects_unknown_providers():
    outcome = _import_with_provider("fmp")

    assert_that(outcome.is_success(), equal_to(False))
    assert_that(
        "; ".join(outcome.errors),
        contains_string("only the 'alpaca' and 'tiingo' providers"),
    )
