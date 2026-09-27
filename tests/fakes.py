"""Shared test doubles."""

import asyncio
import datetime
from collections.abc import AsyncIterator, Callable, Coroutine
from types import SimpleNamespace
from typing import Any, cast

from alpaca.trading.enums import AssetClass, AssetStatus
from hamcrest import assert_that, not_none

from mrmkt.command.start_engine import MessageQueue, PriceProvider
from mrmkt.command.watch import Quote
from mrmkt.common.util import to_date
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.ext.backend import InMemoryBackend
from mrmkt.repo.ticks import LiveTickSource, Tick


class FakeAlpacaClient:
    def __init__(self):
        self.assets = []
        self.error = None

    def get_all_assets(self, filter=None):
        if self.error is not None:
            raise self.error
        return self.assets

    def set_assets(self, rows):
        """Populate the fake catalog from row dicts with symbol/exchange/asset_class/status/tradable."""
        self.assets = [
            SimpleNamespace(
                symbol=row["symbol"],
                exchange=row["exchange"],
                asset_class=AssetClass(row["asset_class"]),
                status=AssetStatus(row["status"]),
                tradable=row["tradable"].lower() == "true",
            )
            for row in rows
        ]


class FakeTickSource(LiveTickSource):
    """Scripted live ticks; holds the stream open after scripts run dry."""

    def __init__(self):
        self._ticks = []

    def add_tick(self, symbol, price, at):
        self._ticks.append(Tick(symbol=symbol, price=price, at=at))

    async def subscribe(self, symbol: str) -> AsyncIterator[Tick]:
        for tick in [tick for tick in self._ticks if tick.symbol == symbol]:
            yield tick
        await asyncio.Event().wait()


class FakeMessageQueue(MessageQueue):
    """Fake queue transport that remembers subscribed subjects."""

    def __init__(self):
        self.subjects = []
        self.messages = []
        self.published = []
        self.on_message: Callable[[str], None] | None = None

    def subscribe(self, subject: str) -> None:
        self.subjects.append(subject)

    def send(self, subject: str, symbol: str) -> None:
        self.messages.append((subject, symbol))
        if self.on_message is not None:
            self.on_message(symbol)

    def publish(self, subject: str, event: Quote) -> None:
        self.published.append((subject, event))


class FakePriceSource(PriceProvider):
    """Push source with scripted subscribers, like the websocket.

    Quotes only flow after a push: subscribe records handlers per symbol
    and push delivers to the handlers currently attached.
    """

    def __init__(self):
        self.subscribed = []
        self.handlers = {}

    def subscribe(self, symbols, *, on_quote) -> None:
        self.subscribed.append(list(symbols))
        for symbol in symbols:
            self.handlers.setdefault(symbol, []).append(on_quote)

    # test method to push quotes to the handlers; not part of the real interface
    def push(self, quotes) -> None:
        for quote in quotes:
            for handler in self.handlers.get(quote.symbol, []):
                handler(quote)


class InMemoryStreamSource:
    """Fake Alpaca websocket: records subscriptions, replays scripted quotes.

    Mirrors the slice of StockDataStream that AlpacaStreamSource uses:
    subscribe_quotes(handler, *symbols) plus run(). Like the real
    dispatcher, handlers are coroutine functions, so replay() drives each
    scripted quote to completion synchronously.
    """

    def __init__(self, quotes=()):
        self.quotes = list(quotes)
        self.quote_handler: Callable[[Any], Coroutine[Any, Any, None]] | None = None
        self.symbols = []

    def subscribe_quotes(self, handler, *symbols):
        self.quote_handler = handler
        self.symbols.extend(symbols)

    def run(self):
        pass

    def replay(self):
        assert_that(self.quote_handler, not_none())
        handler = cast("Callable[[Any], Coroutine[Any, Any, None]]", self.quote_handler)
        for quote in self.quotes:
            asyncio.run(handler(quote))


class _CannedBackend(InMemoryBackend):
    """In-memory backend preloaded with the canned Wall Street dataset."""

    def with_all(self):
        self.add_apple_financials()
        self.add_google_financials()
        self.add_nvidia_financials()
        self.add_spy_financials()
        self.add_walmart()
        self.with_disney()
        return self

    def add_google_financials(self):
        self.add_ticker_only("GOOG")
        self.add_income(
            IncomeStatement(
                symbol="GOOG",
                date=datetime.date(2018, 12, 1),
                netIncome=30736000000.0,
                waso=750000000,
                consolidated_net_income=-1,
            )
        )

        self.add_balance_sheet(
            BalanceSheet(
                symbol="GOOG",
                date=datetime.date(2018, 12, 1),
                totalAssets=232792000000.0,
                totalLiabilities=1264000000.0,
            )
        )

        self.add_price(
            StockPrice(
                symbol="GOOG",
                date=datetime.date(2014, 6, 13),
                open=552.26,
                high=552.3,
                low=545.56,
                close=551.76,
                volume=1217176.0,
            )
        )

        self.add_price(
            StockPrice(
                symbol="GOOG",
                date=datetime.date(2014, 6, 16),
                open=549.26,
                high=549.62,
                low=541.52,
                close=544.28,
                volume=1704027.0,
            )
        )
        self.add_price(
            StockPrice(
                symbol="GOOG",
                date=datetime.date(2018, 11, 30),
                open=1089.07,
                high=1095.57,
                low=1077.88,
                close=1094.43,
                volume=2580612.0,
            )
        )
        self.add_price(
            StockPrice(
                symbol="GOOG",
                date=datetime.date(2018, 12, 3),
                open=1103.12,
                high=1104.42,
                low=1049.98,
                close=1050.82,
                volume=2345166.0,
            )
        )

    def add_nvidia_financials(self):
        self.add_ticker_only("NVDA")
        self.add_income(
            IncomeStatement(
                symbol="NVDA",
                date=datetime.date(2019, 1, 27),
                netIncome=4141000000.0,
                waso=625000000,
                consolidated_net_income=-1,
            )
        )

        self.add_balance_sheet(
            BalanceSheet(
                symbol="NVDA",
                date=datetime.date(2019, 1, 27),
                totalAssets=13292000000.0,
                totalLiabilities=3950000000.0,
            )
        )

        self.add_price(
            StockPrice(
                symbol="NVDA",
                date=datetime.date(2014, 6, 13),
                open=18.8814,
                high=18.891,
                low=18.5272,
                close=18.7091,
                volume=5696281.0,
            )
        )

    def add_apple_financials(self):
        self.add_ticker_only("AAPL")
        self.add_income(
            IncomeStatement(
                symbol="AAPL",
                date=datetime.date(2018, 9, 29),
                netIncome=59531000000.0,
                waso=5000109000,
                consolidated_net_income=-1,
            )
        )

        self.add_balance_sheet(
            BalanceSheet(
                symbol="AAPL",
                date=datetime.date(2018, 9, 29),
                totalAssets=365725000000.0,
                totalLiabilities=258578000000.0,
            )
        )

        self.add_income(
            IncomeStatement(
                symbol="AAPL",
                date=datetime.date(2017, 9, 30),
                netIncome=48351000000.0,
                waso=5251692000,
                consolidated_net_income=-1,
            )
        )

        self.add_balance_sheet(
            BalanceSheet(
                symbol="AAPL",
                date=datetime.date(2017, 9, 30),
                totalAssets=375319000000.0,
                totalLiabilities=241272000000.0,
            )
        )

        self.add_cash_flow(
            CashFlow(
                symbol="AAPL",
                date=datetime.date(2018, 9, 29),
                operating_cash_flow=77434000000.0,
                capital_expenditure=-13313000000.0,
                free_cash_flow=64121000000.0,
                dividend_payments=-13712000000.0,
            )
        )

        self.add_enterprise_value(
            EnterpriseValue(
                symbol="AAPL",
                date=datetime.date(2018, 9, 29),
                stock_price=224.6375,
                shares_outstanding=5000109000.0,
                market_cap=1.1232119854875e12,
            )
        )

        self.add_price(
            StockPrice(
                symbol="AAPL",
                date=datetime.date(2014, 6, 13),
                open=84.5035,
                high=84.7235,
                low=83.2937,
                close=83.6603,
                volume=5.452528e7,
            )
        )

        return self

    def add_spy_financials(self):
        self.add_ticker_only("SPY")

    def add_walmart(self):
        self.add_ticker_only("WMT")

        self.add_income(
            IncomeStatement(
                symbol="WMT",
                date=to_date("2017-01-31"),
                netIncome=13643000000.0,
                waso=3112000000,
                consolidated_net_income=14293000000.0,
            )
        )
        self.add_balance_sheet(
            BalanceSheet(
                symbol="WMT",
                date=to_date("2017-01-31"),
                totalAssets=198825000000.0,
                totalLiabilities=10265000000.0,
                non_current_assets=51362000000.0,
                inventories=43046000000.0,
                receivables=5835000000.0,
            )
        )
        self.add_cash_flow(
            CashFlow(
                symbol="WMT",
                date=to_date("2017-01-31"),
                operating_cash_flow=-31673000000.0,
                capital_expenditure=-10163000000.0,
                free_cash_flow=21510000000.0,
                dividend_payments=-6216000000.0,
            )
        )
        self.add_enterprise_value(
            EnterpriseValue(
                symbol="WMT",
                date=to_date("2017-01-31"),
                stock_price=62.5478,
                shares_outstanding=3112000000.0,
                market_cap=1.946487536e11,
            )
        )

    def with_disney(self):
        self.add_ticker_only("DIS")

        self.add_income(
            IncomeStatement(
                symbol="DIS",
                date=to_date("2018-09-29"),
                netIncome=12598000000.0,
                waso=1507000000,
                consolidated_net_income=13066000000.0,
            )
        )
        self.add_balance_sheet(
            BalanceSheet(
                symbol="DIS",
                date=to_date("2018-09-29"),
                totalAssets=98598000000.0,
                totalLiabilities=45766000000.0,
                non_current_assets=27906000000.0,
                inventories=1392000000.0,
                receivables=9334000000.0,
            )
        )
        self.add_cash_flow(
            CashFlow(
                symbol="DIS",
                date=to_date("2018-09-29"),
                operating_cash_flow=14295000000.0,
                capital_expenditure=-4465000000.0,
                free_cash_flow=9830000000.0,
                deprec=3011000000.0,
                dividend_payments=-2515000000.0,
            )
        )
        self.add_enterprise_value(
            EnterpriseValue(
                symbol="DIS",
                date=to_date("2018-09-29"),
                stock_price=115.3453,
                shares_outstanding=1507000000,
                market_cap=1.738253671e11,
            )
        )

        return self


def canned_backend() -> InMemoryBackend:
    """Fresh in-memory backend preloaded with the canned Wall Street dataset."""
    return _CannedBackend().with_all()
