"""Postgres ticker-tag repository (mixin)."""

from dataclasses import dataclass

from mrmkt.common.sql import SqlClient
from mrmkt.entity.ticker import Ticker
from mrmkt.ext.repo.postgres.tickers import PostgresTickerRepository
from mrmkt.repo.tags import TickerTagRepository


class PostgresTagRepository(TickerTagRepository, PostgresTickerRepository):
    """Ticker tags over SQL; combined via PostgresBackend."""

    # Inherits ticker listing: tag queries filter the ticker catalog.

    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def add_tag(self, ticker: str, exchange: str, tag: str) -> None:
        self.sql_client.insert("ticker_tag", TickerTagRow(ticker, exchange, tag))

    def remove_tag(self, ticker: str, exchange: str, tag: str) -> bool:
        return self.sql_client.delete(
            "delete from ticker_tag where ticker = %s and exchange = %s and tag = %s",
            (ticker, exchange, tag),
        )

    def get_tags(self, ticker: str, exchange: str) -> list[str]:
        rows = self.sql_client.select(
            "select ticker, exchange, tag from ticker_tag",
            lambda row: row,
        )
        return sorted(
            row["tag"]
            for row in rows
            if row["ticker"] == ticker and row["exchange"] == exchange
        )

    def list_tickers_by_tag(self, tag: str) -> list[Ticker]:
        rows = self.sql_client.select(
            "select ticker, exchange, tag from ticker_tag",
            lambda row: row,
        )
        tagged = {(row["ticker"], row["exchange"]) for row in rows if row["tag"] == tag}
        return sorted(
            (
                ticker
                for ticker in self.get_tickers()
                if (ticker.ticker, ticker.exchange) in tagged
            ),
            key=lambda ticker: (ticker.ticker, ticker.exchange),
        )

    def get_symbols_by_tag(self, tag: str) -> list[str]:
        return sorted({ticker.ticker for ticker in self.list_tickers_by_tag(tag)})


@dataclass
class TickerTagRow:
    ticker: str
    exchange: str
    tag: str
