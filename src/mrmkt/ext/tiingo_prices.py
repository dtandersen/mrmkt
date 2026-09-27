"""Tiingo daily-price adapter (outer layer, ``mrmkt.ext``).

Batch ``get_prices`` interface matching :class:`AlpacaPriceSource` so the
``ImportPrices`` command can use either provider. The API key comes from
the ``TIINGO_API_KEY`` environment variable; tests inject a stub
``http_get`` instead of touching the network.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date
from typing import Any

import requests

from mrmkt.command.base import Log
from mrmkt.common.util import to_date
from mrmkt.entity.stock_price import StockPrice

TIINGO_API_KEY_ENV_VAR = "TIINGO_API_KEY"
BASE_URL = "https://api.tiingo.com/tiingo/daily"


class TiingoPriceSource:
    """Fetch split- and dividend-adjusted daily bars from Tiingo."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        http_get: Callable[..., Any] | None = None,
        log: Log,
    ):
        key = api_key if api_key is not None else os.environ.get(TIINGO_API_KEY_ENV_VAR)
        if not key:
            raise ValueError(
                f"{TIINGO_API_KEY_ENV_VAR} environment variable is not set"
            )
        self.api_key = key
        self.http_get = http_get or requests.get
        self.log = log

    @classmethod
    def from_env(
        cls, log: Log, *, http_get: Callable[..., Any] | None = None
    ) -> TiingoPriceSource:
        """Build a source from the ``TIINGO_API_KEY`` environment variable."""
        return cls(api_key=None, http_get=http_get, log=log)

    def get_prices(
        self,
        symbols: list[str],
        start: date,
        end: date,
    ) -> dict[str, list[StockPrice]]:
        if start > end:
            raise ValueError("start date must not be after end date")

        normalized_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols))
        if not normalized_symbols:
            return {}

        self.log("Connected to Tiingo prices")
        self.log(f"Subscribing to {', '.join(normalized_symbols)}")

        return {
            symbol: self._get_symbol_prices(symbol, start, end)
            for symbol in normalized_symbols
        }

    def _get_symbol_prices(
        self, symbol: str, start: date, end: date
    ) -> list[StockPrice]:
        response = self.http_get(
            f"{BASE_URL}/{symbol}/prices",
            params={
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "format": "json",
            },
            headers={"Authorization": f"Token {self.api_key}"},
            timeout=30,
        )
        response.raise_for_status()
        return [self.map_price(row, symbol) for row in response.json()]

    @staticmethod
    def map_price(row: dict, symbol: str) -> StockPrice:
        return StockPrice(
            symbol=symbol,
            date=to_date(row["date"][0:10]),
            open=_adjusted(row, "adjOpen", "open"),
            high=_adjusted(row, "adjHigh", "high"),
            low=_adjusted(row, "adjLow", "low"),
            close=_adjusted(row, "adjClose", "close"),
            volume=row["volume"],
        )


def _adjusted(row: dict, adj_key: str, raw_key: str) -> float:
    """Prefer the split/dividend-adjusted field; fall back to the raw one."""
    value = row.get(adj_key)
    return value if value is not None else row[raw_key]
