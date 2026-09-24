"""Shared entrypoint plumbing for mrmkt commands.

Factories, name normalization, and date parsing live here so each
command module stays focused on its own options and use-case calls.
``mrmkt.cli`` re-exports these names for backwards compatibility
(scanner.py and the test suite import them from there).
"""

import re
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import typer
import yaml
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from psycopg2.pool import SimpleConnectionPool

from mrmkt.common.clock import Clock, WallClock
from mrmkt.common.sql import InsecureSqlGenerator
from mrmkt.common.sqlfinrepo import SqlFinancialRepository
from mrmkt.ext.postgres import PostgresSqlClient


def create_clock() -> Clock:
    return WallClock()


def parse_cli_date(value: str, today: date) -> date:
    normalized = value.strip().lower()
    if normalized in {"now", "today"}:
        return today

    relative = re.fullmatch(r"(\d+)\s*(?:d|days?)(?:\s+ago)?", normalized)
    if relative:
        try:
            days = int(relative.group(1))
        except ValueError as error:
            raise ValueError("invalid relative date") from error
        return today - timedelta(days=days)

    return date.fromisoformat(normalized)


def normalize_tag(tag: str) -> str:
    normalized = tag.strip().lower()
    if re.fullmatch(r"[a-z0-9][a-z0-9_-]*", normalized) is None:
        raise typer.BadParameter("tags must start with a letter or number and contain only letters, numbers, '_' or '-'")
    return normalized


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if re.fullmatch(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*", normalized) is None:
        raise typer.BadParameter(f"invalid stock symbol: {symbol}")
    return normalized


def split_benchmark_symbol(
    selected: list[str], benchmark_symbol: str
) -> tuple[list[str], str | None]:
    """Split the benchmark out of the tradable symbol list.

    The benchmark is non-tradable context, so it is excluded — unless
    it is the sole selected symbol, in which case it is kept as both
    benchmark and tradable (with a note) so `backtest run SPY` keeps
    working. Returns the tradables plus an optional note to echo."""
    if not benchmark_symbol or benchmark_symbol not in selected:
        return selected, None
    if len(selected) == 1:
        return selected, (
            f"Benchmark {benchmark_symbol} is the sole selected symbol; "
            "it is traded as well as used for gating."
        )
    return (
        [s for s in selected if s != benchmark_symbol],
        f"Benchmark {benchmark_symbol} excluded from tradable symbols.",
    )


# These factories are small seams for BDD tests: tests replace them with a fake
# Alpaca client and an in-memory ticker repository.
def create_alpaca_client() -> TradingClient:
    config = yaml.safe_load(Path("alpaca.yaml").read_text())
    endpoint = config["endpoint"].rstrip("/")
    parsed_endpoint = urlsplit(endpoint)
    if parsed_endpoint.hostname != "paper-api.alpaca.markets":
        raise ValueError("Symbol import is restricted to the Alpaca paper endpoint")

    # TradingClient adds its API version itself; the local config includes /v2.
    base_url = endpoint.removesuffix("/v2")
    return TradingClient(
        api_key=config["key"],
        secret_key=config["secret"],
        paper=True,
        url_override=base_url,
    )


def create_local_ticker_repository() -> tuple[SqlFinancialRepository, Callable[[], None]]:
    config = yaml.safe_load(Path("dbschema.yml").read_text())
    db_config = config["databases"]["db1"]
    pool = SimpleConnectionPool(
        1,
        5,
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["db"],
    )
    sql_client = PostgresSqlClient(InsecureSqlGenerator(), pool)
    return SqlFinancialRepository(sql_client), pool.closeall


def create_alpaca_data_client() -> StockHistoricalDataClient:
    config = yaml.safe_load(Path("alpaca.yaml").read_text())
    return StockHistoricalDataClient(
        api_key=config["key"],
        secret_key=config["secret"],
    )


def load_local_config() -> dict:
    """Read optional local config.yaml; missing/invalid means {} (never raises)."""
    try:
        text = Path("config.yaml").read_text()
    except OSError:
        return {}
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_signal(signal: str) -> str:
    normalized = (signal or "").strip().lower()
    if normalized != "risk-range":
        raise typer.BadParameter(
            f"unknown signal {signal!r} (only 'risk-range' is supported)"
        )
    return normalized
