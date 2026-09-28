"""Scripting facade tests (in-memory backend, no DB or network)."""

import threading
import time
from datetime import UTC, date, datetime, timedelta

import pytest
from tests.fakes import FakeMessageQueue

import mrmkt
from mrmkt.command.start_engine import DEFAULT_SUBJECT
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.ext.backend import InMemoryBackend
from mrmkt.gateway import Quote
from mrmkt.scripting import MrMkt


def _seed(repo, symbol="SPY", bars=40):
    price = 400.0
    for day in range(bars):
        # Alternate daily moves so realized volatility is nonzero.
        price *= 1.002 if day % 2 == 0 else 0.999
        repo.add_price(
            StockPrice(
                symbol=symbol,
                date=date(2024, 1, 2) + timedelta(days=day),
                open=price,
                high=price * 1.005,
                low=price * 0.995,
                close=price,
                volume=1_000_000.0,
            )
        )


def _session(financial_repository, **kwargs):
    return MrMkt(
        cli_dependencies_for_testing(repository=financial_repository, **kwargs)
    )


def test_prices_of_symbol_returns_oldest_first(financial_repository):
    _seed(financial_repository)
    with _session(financial_repository) as mkt:
        bars = mkt.prices_historical.of_symbol("SPY")
    assert len(bars) == 40
    assert [bar.date for bar in bars] == sorted(bar.date for bar in bars)
    assert all(bar.symbol == "SPY" for bar in bars)


def test_prices_latest_returns_most_recent_bar(financial_repository):
    _seed(financial_repository)
    with _session(financial_repository) as mkt:
        row = mkt.prices_historical.latest("SPY")
    assert row.symbol == "SPY"
    assert row.date == date(2024, 1, 2) + timedelta(days=39)


def test_prices_latest_without_history(financial_repository):
    with _session(financial_repository) as mkt, pytest.raises(LookupError):
        mkt.prices_historical.latest("SPY")


def test_symbols_with_tag_lists_tickers(financial_repository):
    financial_repository.add_ticker(
        Ticker(ticker="AAPL", exchange="NASDAQ", type="us_equity")
    )
    financial_repository.add_ticker(
        Ticker(ticker="MSFT", exchange="NASDAQ", type="us_equity")
    )
    financial_repository.add_tag("AAPL", "NASDAQ", "sp500")
    with _session(financial_repository) as mkt:
        assert mkt.symbols.with_tag("sp500") == ["AAPL"]


def test_context_manager_releases_resources(financial_repository):
    released = []
    with _session(
        financial_repository,
        repository_release=lambda: released.append(True),
    ):
        pass
    assert released == [True]


def test_prices_import_rejects_unknown_provider(financial_repository):
    with _session(financial_repository) as mkt, pytest.raises(ValueError):
        mkt.prices_historical.import_history(["SPY"], provider="bogus", from_date="7d")


def test_empty_in_memory_store_and_release():
    with (
        MrMkt(cli_dependencies_for_testing(repository=InMemoryBackend())) as session,
        pytest.raises(LookupError),
    ):
        assert session.symbols.with_tag("sp500") == []
        session.prices_historical.latest("SPY")


def test_realtime_latest_returns_bus_quote(financial_repository):
    queue = FakeMessageQueue()
    session = MrMkt(
        cli_dependencies_for_testing(
            repository=financial_repository, engine_queue=queue
        )
    )
    quote = Quote(
        symbol="SPY",
        bid=770.0,
        ask=771.0,
        timestamp=datetime.now(tz=UTC),
    )
    out = {}
    worker = threading.Thread(
        target=lambda: out.setdefault(
            "quote", session.prices_realtime.latest("SPY", timeout=5)
        ),
        daemon=True,
    )
    worker.start()
    for _ in range(500):
        if queue.subjects:
            break
        time.sleep(0.01)
    queue.deliver(f"{DEFAULT_SUBJECT}.SPY", quote)
    worker.join(timeout=10)
    assert out["quote"] == quote
    session.close()


def test_realtime_latest_times_out_without_flow(financial_repository):
    queue = FakeMessageQueue()
    session = MrMkt(
        cli_dependencies_for_testing(
            repository=financial_repository, engine_queue=queue
        )
    )
    try:
        with pytest.raises(LookupError):
            session.prices_realtime.latest("SPY", timeout=1)
    finally:
        session.close()


def test_features_accessor_round_trip(financial_repository):
    from mrmkt.entity.ticker import Ticker as _Ticker

    financial_repository.add_ticker(
        _Ticker(ticker="SPY", exchange="NASDAQ", type="us_equity")
    )
    session = MrMkt(cli_dependencies_for_testing(repository=financial_repository))
    try:
        row = session.features.create("SPY", "rr15.low=760.42", "2026-09-24")
        assert row.value_num == 760.42
        assert session.features.latest("SPY", "rr15.low").value_num == 760.42
        assert len(session.features.of_symbol("SPY")) == 1
        with pytest.raises(LookupError):
            session.features.latest("SPY", "nope")
        with pytest.raises(ValueError):
            session.features.create("SPY", "badassignment", "2026-09-24")
    finally:
        session.close()


def test_connect_is_exposed_on_package():
    assert callable(mrmkt.connect)
