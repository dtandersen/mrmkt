"""Tests for Yahoo Finance's daily chart-price adapter."""

from datetime import UTC, date, datetime, time

from hamcrest import assert_that, contains_string, equal_to
from tests.fakes import CapturingLog

from mrmkt.entity.stock_price import StockPrice
from mrmkt.ext.yahoo_prices import BASE_URL, YahooFinancePriceSource

START = date(2026, 9, 25)
END = date(2026, 9, 25)


class StubResponse:
    def __init__(self, payload, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


class StubHttp:
    """Stub HTTP transport recording calls and returning one chart response."""

    def __init__(self, payload=None, error=None):
        self.payload = payload or {}
        self.error = error
        self.calls = []

    def __call__(self, url, *, params=None, headers=None, timeout=None):
        self.calls.append(
            {"url": url, "params": params, "headers": headers, "timeout": timeout}
        )
        return StubResponse(self.payload, self.error)


def _timestamp(day):
    return int(datetime.combine(day, time.min, UTC).timestamp())


def _payload(day, *, close=14.87, adjclose=14.87):
    return {
        "chart": {
            "result": [
                {
                    "timestamp": [_timestamp(day)],
                    "indicators": {
                        "quote": [
                            {
                                "open": [15.61],
                                "high": [15.94],
                                "low": [14.68],
                                "close": [close],
                                "volume": [0],
                            }
                        ],
                        "adjclose": [{"adjclose": [adjclose]}],
                    },
                }
            ],
            "error": None,
        }
    }


def _source(http, log=None):
    return YahooFinancePriceSource(http_get=http, log=log or CapturingLog())


def test_vix_alias_maps_to_yahoo_index_and_inclusive_date_window():
    http = StubHttp(_payload(START))
    log = CapturingLog()

    prices = _source(http, log=log).get_prices(["vix", "VIX"], START, END)

    assert_that(
        prices,
        equal_to(
            {
                "VIX": [
                    StockPrice(
                        symbol="VIX",
                        date=START,
                        open=15.61,
                        high=15.94,
                        low=14.68,
                        close=14.87,
                        volume=0,
                    )
                ]
            }
        ),
    )
    assert_that(len(http.calls), equal_to(1))
    call = http.calls[0]
    assert_that(call["url"], equal_to(f"{BASE_URL}/%5EVIX"))
    assert_that(
        call["params"],
        equal_to(
            {
                "period1": _timestamp(START),
                "period2": _timestamp(END) + 24 * 60 * 60,
                "interval": "1d",
                "events": "div,splits",
                "includeAdjustedClose": "true",
            }
        ),
    )
    assert_that(
        log.lines,
        equal_to(
            [
                "Connected to Yahoo Finance prices",
                "Subscribing to VIX (^VIX)",
            ]
        ),
    )


def test_adjusts_ohlc_using_yahoo_adjusted_close():
    payload = _payload(date(2024, 1, 2), close=100, adjclose=90)
    payload["chart"]["result"][0]["indicators"]["quote"][0].update(
        {"open": [98], "high": [101], "low": [97]}
    )
    http = StubHttp(payload)

    prices = _source(http).get_prices(["ABC"], date(2024, 1, 2), date(2024, 1, 2))

    bar = prices["ABC"][0]
    assert_that(
        (bar.open, bar.high, bar.low, bar.close), equal_to((88.2, 90.9, 87.3, 90.0))
    )


def test_skips_incomplete_yahoo_daily_rows():
    payload = _payload(START)
    payload["chart"]["result"][0]["timestamp"].append(_timestamp(END) + 86400)
    for key in ("open", "high", "low", "close", "volume"):
        payload["chart"]["result"][0]["indicators"]["quote"][0][key].append(None)
    payload["chart"]["result"][0]["indicators"]["adjclose"][0]["adjclose"].append(None)

    prices = _source(StubHttp(payload)).get_prices(["VIX"], START, END)

    assert_that(len(prices["VIX"]), equal_to(1))


def test_chart_level_error_propagates_for_import_failure_accounting():
    http = StubHttp(
        {"chart": {"result": None, "error": {"description": "symbol not found"}}}
    )

    try:
        _source(http).get_prices(["VIX"], START, END)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as error:
        assert_that(str(error), contains_string("symbol not found"))


def test_reversed_window_is_rejected_before_request():
    http = StubHttp(_payload(START))

    try:
        _source(http).get_prices(["VIX"], date(2026, 9, 26), START)
        raise AssertionError("expected ValueError")
    except ValueError as error:
        assert_that(
            str(error), contains_string("start date must not be after end date")
        )
    assert_that(http.calls, equal_to([]))


def test_empty_symbol_list_is_a_noop():
    http = StubHttp(_payload(START))

    assert_that(_source(http).get_prices([], START, END), equal_to({}))
    assert_that(http.calls, equal_to([]))
