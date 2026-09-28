"""Scripting facade tests (in-memory backend, no DB or network)."""

from datetime import date, timedelta

import mrmkt
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
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
        bars = mkt.prices.of_symbol("SPY")
    assert len(bars) == 40
    assert [bar.date for bar in bars] == sorted(bar.date for bar in bars)
    assert all(bar.symbol == "SPY" for bar in bars)


def test_prices_latest_returns_most_recent_bar(financial_repository):
    _seed(financial_repository)
    with _session(financial_repository) as mkt:
        row = mkt.prices.latest("SPY")
    assert row.symbol == "SPY"
    assert row.date == date(2024, 1, 2) + timedelta(days=39)


def test_prices_latest_without_history(financial_repository):
    with _session(financial_repository) as mkt:
        try:
            mkt.prices.latest("SPY")
        except LookupError:
            return
    raise AssertionError("expected LookupError for missing symbol")


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


def test_connect_is_exposed_on_package():
    assert callable(mrmkt.connect)
