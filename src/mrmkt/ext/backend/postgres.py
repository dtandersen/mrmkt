"""Postgres whole-service backend (client + composed repositories)."""

import dataclasses
import datetime
import json
import logging
import re
from collections.abc import Callable
from dataclasses import asdict
from typing import Any, cast

import psycopg2
import psycopg2.extras
from psycopg2 import sql as pg_sql
from psycopg2.pool import AbstractConnectionPool

from mrmkt.backend import MrMktBackend
from mrmkt.common.sql import Duplicate, JsonField, SqlClient
from mrmkt.common.util import EnhancedJSONEncoder
from mrmkt.entity.analysis import Analysis
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.entity.trigger import Trigger
from mrmkt.ext.repo.postgres.features import PostgresFeatureRepository
from mrmkt.ext.repo.postgres.financials import PostgresFinancialRepository
from mrmkt.ext.repo.postgres.prices import PostgresPriceRepository
from mrmkt.ext.repo.postgres.tags import PostgresTagRepository
from mrmkt.ext.repo.postgres.tickers import PostgresTickerRepository
from mrmkt.ext.repo.postgres.trigger_sets import PostgresTriggerSetRepository
from mrmkt.ext.repo.postgres.triggers import PostgresTriggerRepository
from mrmkt.repo.features import FeatureRepository

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _validate_identifier(name: str) -> str:
    """Allow only simple application-owned table/column identifiers."""
    if not _IDENTIFIER_RE.fullmatch(name):
        raise ValueError(f"invalid SQL identifier: {name!r}")
    return name


def _map_value(value: Any) -> Any:
    if isinstance(value, JsonField):
        return json.dumps(value.data, cls=EnhancedJSONEncoder)
    if isinstance(value, dict):  # asdict() form of a JsonField
        return json.dumps(value["data"], cls=EnhancedJSONEncoder)
    return value


def build_insert(table: str, values: Any) -> tuple[pg_sql.Composable, tuple]:
    """Build an insert using SQL identifiers and bound data values."""
    d: dict[str, Any]
    if dataclasses.is_dataclass(values) and not isinstance(values, type):
        d = asdict(values)
    else:
        d = cast(dict[str, Any], values)
    if not d:
        raise ValueError("insert requires at least one column")
    columns = pg_sql.SQL(", ").join(
        pg_sql.Identifier(_validate_identifier(key)) for key in d
    )
    placeholders = pg_sql.SQL(", ").join(pg_sql.Placeholder() for _ in d)
    query = pg_sql.SQL("insert into {} ({}) values ({})").format(
        pg_sql.Identifier(_validate_identifier(table)), columns, placeholders
    )
    return query, tuple(_map_value(value) for value in d.values())


class PostgresSqlClient(SqlClient):
    def __init__(self, pool: AbstractConnectionPool):
        self.pool = pool

    def select(self, query: str, mapper: Callable[[dict], object], params: tuple = ()):
        conn = self.pool.getconn()
        try:
            with (
                conn,
                conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur,
            ):
                sql = query
                cur.execute(sql, params)
                rows = cur.fetchall()
                # rows = list(map(lambda x: x[0], cur.description))
                logging.debug(f"{sql} => {rows}")
                # x = [mapper(row) for row in rows]
                # logging.debug(f"{sql} => {x}")
                # z= psycopg2.RealDictRow()
                r2 = [mapper(dict(row)) for row in rows]
                # logging.debug(f"{sql} => {r2}")
                return r2
        finally:
            self.pool.putconn(conn)

    def insert(self, table: str, values: Any):
        conn = self.pool.getconn()
        try:
            with conn, conn.cursor() as cur:
                sql, params = build_insert(table, values)
                logging.debug(sql)
                try:
                    cur.execute(sql, params)
                except psycopg2.errors.UniqueViolation as err:
                    raise Duplicate(err) from err
        finally:
            self.pool.putconn(conn)

    def delete(self, query: str, params: tuple = ()) -> bool:
        conn = self.pool.getconn()
        try:
            with (
                conn,
                conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur,
            ):
                sql = query
                cur.execute(sql, params)
                return cur.rowcount > 0
        finally:
            self.pool.putconn(conn)


class PostgresBackend(MrMktBackend, FeatureRepository):
    """Whole-service Postgres backend delegating to narrow repositories.

    Composition instead of multiple inheritance: MI of the narrow
    mixins plus the wide bundle is not C3-linearizable in any order,
    while forwarding stays trivially correct.
    """

    def __init__(self, sql_client: SqlClient):
        self._features = PostgresFeatureRepository(sql_client)
        self._financials = PostgresFinancialRepository(sql_client)
        self._prices = PostgresPriceRepository(sql_client)
        self._tickers = PostgresTickerRepository(sql_client)
        self._tags = PostgresTagRepository(sql_client)
        self._triggers = PostgresTriggerRepository(sql_client)
        self._sets = PostgresTriggerSetRepository(sql_client)

    def close(self) -> None:
        """No-op: the pool lifecycle stays with the composition root."""

    def list_balance_sheets(self, symbol: str):
        return self._financials.list_balance_sheets(symbol)

    def add_balance_sheet(self, balance_sheet: BalanceSheet):
        return self._financials.add_balance_sheet(balance_sheet)

    def get_income_statements(self, symbol: str) -> list[IncomeStatement]:
        return self._financials.get_income_statements(symbol)

    def add_income(self, income_statement: IncomeStatement):
        return self._financials.add_income(income_statement)

    def get_cash_flow(self, symbol: str, date: datetime.date) -> CashFlow:
        return self._financials.get_cash_flow(symbol, date)

    def add_cash_flow(self, cash_flow: CashFlow):
        return self._financials.add_cash_flow(cash_flow)

    def get_enterprise_value(self, symbol: str, date: datetime.date) -> EnterpriseValue:
        return self._financials.get_enterprise_value(symbol, date)

    def add_enterprise_value(self, enterprise_value: EnterpriseValue):
        return self._financials.add_enterprise_value(enterprise_value)

    def add_analysis(self, analysis: Analysis):
        return self._financials.add_analysis(analysis)

    def delete_analysis(self, symbol: str, date: datetime.date):
        return self._financials.delete_analysis(symbol, date)

    def get_income_statement(
        self, symbol: str, date: datetime.date
    ) -> list[IncomeStatement]:
        return self._financials.get_income_statement(symbol, date)

    def list_income_statements(self, symbol: str) -> list[IncomeStatement]:
        return self._financials.list_income_statements(symbol)

    def get_balance_sheet(self, symbol, date: datetime.date) -> list[BalanceSheet]:
        return self._financials.get_balance_sheet(symbol, date)

    def list_cash_flows(self, symbol: str) -> list[CashFlow]:
        return self._financials.list_cash_flows(symbol)

    def list_enterprise_value(self, symbol: str) -> list[EnterpriseValue]:
        return self._financials.list_enterprise_value(symbol)

    def add_price(self, price: StockPrice):
        return self._prices.add_price(price)

    def add_feature(self, feature):
        return self._features.add_feature(feature)

    def delete_features(self, symbol: str, feature: str) -> int:
        return self._features.delete_features(symbol, feature)

    def list_features(
        self,
        symbol: str,
        feature: str | None = None,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ):
        return self._features.list_features(symbol, feature, start, end)

    def list_prices(
        self,
        ticker: str,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[StockPrice]:
        return self._prices.list_prices(ticker, start, end)

    def list_prices_for_symbols(
        self,
        tickers: list[str],
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[StockPrice]:
        return self._prices.list_prices_for_symbols(tickers, start, end)

    def get_price(self, symbol: str, date: str) -> StockPrice:
        return self._prices.get_price(symbol, date)

    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        return self._prices.get_price_on_or_after(symbol, date)

    def get_symbols(self) -> list[str]:
        return self._tickers.get_symbols()

    def get_tickers(self) -> list[Ticker]:
        return self._tickers.get_tickers()

    def list_tickers_by_symbol(self, symbol: str) -> list[Ticker]:
        return self._tickers.list_tickers_by_symbol(symbol)

    def add_ticker(self, ticker: Ticker):
        return self._tickers.add_ticker(ticker)

    def add_tag(self, ticker: str, exchange: str, tag: str) -> None:
        return self._tags.add_tag(ticker, exchange, tag)

    def remove_tag(self, ticker: str, exchange: str, tag: str) -> bool:
        return self._tags.remove_tag(ticker, exchange, tag)

    def get_tags(self, ticker: str, exchange: str) -> list[str]:
        return self._tags.get_tags(ticker, exchange)

    def list_tickers_by_tag(self, tag: str) -> list[Ticker]:
        return self._tags.list_tickers_by_tag(tag)

    def get_symbols_by_tag(self, tag: str) -> list[str]:
        return self._tags.get_symbols_by_tag(tag)

    def list_triggers(self, enabled_only: bool = False) -> list[Trigger]:
        return self._triggers.list_triggers(enabled_only)

    def add_trigger(self, trigger: Trigger) -> Trigger:
        return self._triggers.add_trigger(trigger)

    def remove_trigger(self, trigger_id: int) -> bool:
        return self._triggers.remove_trigger(trigger_id)

    def set_trigger_enabled(self, trigger_id: int, enabled: bool) -> bool:
        return self._triggers.set_trigger_enabled(trigger_id, enabled)

    def create_set(self, name: str) -> str:
        return self._sets.create_set(name)

    def add_to_set(self, set_name: str, trigger_name: str) -> None:
        return self._sets.add_to_set(set_name, trigger_name)

    def remove_from_set(self, set_name: str, trigger_name: str) -> bool:
        return self._sets.remove_from_set(set_name, trigger_name)

    def list_set_members(self, set_name: str) -> list[str]:
        return self._sets.list_set_members(set_name)
