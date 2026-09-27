"""Postgres price repository (mixin)."""

import datetime
import re
from dataclasses import dataclass

from mrmkt.common.sql import SqlClient
from mrmkt.entity.stock_price import StockPrice
from mrmkt.repo.prices import PriceRepository


class PostgresPriceRepository(PriceRepository):
    """Daily bars over SQL; combined via PostgresBackend."""

    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def add_price(self, price: StockPrice):
        row = PriceRow(
            symbol=price.symbol,
            date=price.date,
            open=price.open,
            high=price.high,
            low=price.low,
            close=price.close,
            volume=price.volume,
        )

        self.sql_client.insert("daily_price", row)

    def list_prices(
        self,
        ticker: str,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[StockPrice]:
        start_sql = ""
        end_sql = ""
        params: list = [ticker]
        if start is not None:
            start_sql = "and date >= %s "
            params.append(start.strftime("%Y-%m-%d"))

        if end is not None:
            end_sql = "and date <= %s "
            params.append(end.strftime("%Y-%m-%d"))

        rows = self.sql_client.select(
            "select * "
            + "from daily_price "
            + "where symbol = %s "
            + start_sql
            + end_sql
            + "order by date asc",
            self.price_mapper,
            tuple(params),
        )

        return rows

    def list_prices_for_symbols(
        self,
        tickers: list[str],
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[StockPrice]:
        normalized = []
        for ticker in tickers:
            symbol = ticker.strip().upper()
            if re.fullmatch(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*", symbol) is None:
                raise ValueError(f"invalid stock symbol: {ticker}")
            normalized.append(symbol)
        if not normalized:
            return []
        start_sql = ""
        end_sql = ""
        params: list = [tuple(normalized)]
        if start is not None:
            start_sql = "and date >= %s "
            params.append(start.strftime("%Y-%m-%d"))
        if end is not None:
            end_sql = "and date <= %s "
            params.append(end.strftime("%Y-%m-%d"))
        return self.sql_client.select(
            "select * "
            + "from daily_price "
            + "where symbol in %s "
            + start_sql
            + end_sql
            + "order by symbol asc, date asc",
            self.price_mapper,
            tuple(params),
        )

    def get_price(self, symbol: str, date: str) -> StockPrice:
        rows = self.sql_client.select(
            "select * " + "from daily_price " + "where symbol = %s " + "and date = %s",
            self.price_mapper,
            (symbol, date),
        )

        return rows[0]

    def price_mapper(self, row):
        return StockPrice(
            symbol=row["symbol"],
            date=row["date"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
        )

    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        rows = self.sql_client.select(
            "select * " + "from daily_price " + "where symbol = %s " + "and date >= %s",
            self.price_mapper,
            (symbol, date),
        )

        return rows[0]


@dataclass
class PriceRow:
    symbol: str
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class SymbolRow:
    symbol: str
