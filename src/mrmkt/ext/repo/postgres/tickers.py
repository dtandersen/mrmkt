"""Postgres ticker repository (mixin)."""

from dataclasses import dataclass

from mrmkt.common.sql import SqlClient
from mrmkt.entity.ticker import Ticker
from mrmkt.repo.tickers import TickerRepository


class PostgresTickerRepository(TickerRepository):
    """Tickers over SQL; combined via PostgresBackend."""

    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def get_tickers(self) -> list[Ticker]:
        rows = self.sql_client.select("select * " + "from ticker", self.ticker_mapper)

        return rows

    def ticker_mapper(self, row):
        return Ticker(ticker=row["ticker"], exchange=row["exchange"], type=row["type"])

    def add_ticker(self, ticker: Ticker):
        row = TickerRow(
            ticker=ticker.ticker, exchange=ticker.exchange, type=ticker.type
        )

        self.sql_client.insert("ticker", row)

    def get_symbols(self) -> list[str]:
        rows = self.sql_client.select(
            "select distinct symbol " + "from daily_price ", self.symbol_mapper
        )

        return rows

    def symbol_mapper(self, row):
        return row["symbol"]


@dataclass
class TickerRow:
    ticker: str
    exchange: str
    type: str
