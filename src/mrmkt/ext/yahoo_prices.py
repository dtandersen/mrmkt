"""Yahoo Finance daily-price adapter for the unofficial chart endpoint.

Yahoo's chart API is public and unauthenticated, but is not an official
contract and may rate-limit clients. The local alias ``VIX`` maps to Yahoo's
index symbol ``^VIX`` so it can pass the application's ticker normalization.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import quote

import requests

from mrmkt.command.base import Log
from mrmkt.entity.stock_price import StockPrice

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
USER_AGENT = "Mozilla/5.0 (compatible; MrMkt/0.1; price-history)"
YAHOO_SYMBOL_ALIASES = {"VIX": "^VIX"}


class YahooFinancePriceSource:
    """Fetch split/dividend-adjusted daily bars from Yahoo Finance's chart API."""

    def __init__(
        self,
        *,
        http_get: Callable[..., Any] | None = None,
        log: Log,
    ):
        self.http_get = http_get or requests.get
        self.log = log

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

        self.log("Connected to Yahoo Finance prices")
        subscribed = [
            f"{symbol} ({_yahoo_symbol(symbol)})"
            if _yahoo_symbol(symbol) != symbol
            else symbol
            for symbol in normalized_symbols
        ]
        self.log(f"Subscribing to {', '.join(subscribed)}")
        return {
            symbol: self._get_symbol_prices(symbol, _yahoo_symbol(symbol), start, end)
            for symbol in normalized_symbols
        }

    def _get_symbol_prices(
        self, symbol: str, yahoo_symbol: str, start: date, end: date
    ) -> list[StockPrice]:
        epoch = date(1970, 1, 1)
        period1 = (start - epoch).days * 86_400
        period2 = (end + timedelta(days=1) - epoch).days * 86_400
        response = self.http_get(
            f"{BASE_URL}/{quote(yahoo_symbol, safe='')}",
            params={
                "period1": period1,
                "period2": period2,
                "interval": "1d",
                "events": "div,splits",
                "includeAdjustedClose": "true",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        chart = payload.get("chart", {})
        error = chart.get("error")
        if error:
            description = (
                error.get("description", str(error))
                if isinstance(error, dict)
                else str(error)
            )
            raise RuntimeError(
                f"Yahoo Finance chart error for {yahoo_symbol}: {description}"
            )

        results = chart.get("result") or []
        if not results:
            return []
        result = results[0]
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators") or {}
        quotes = indicators.get("quote") or []
        if not timestamps or not quotes:
            return []

        quote_data = quotes[0]
        adjusted_data = indicators.get("adjclose") or []
        adjusted_closes = adjusted_data[0].get("adjclose") if adjusted_data else None
        prices = []
        for index, timestamp in enumerate(timestamps):
            open_price = _value_at(quote_data.get("open"), index)
            high = _value_at(quote_data.get("high"), index)
            low = _value_at(quote_data.get("low"), index)
            close = _value_at(quote_data.get("close"), index)
            volume_value = _value_at(quote_data.get("volume"), index)
            if (
                timestamp is None
                or open_price is None
                or high is None
                or low is None
                or close is None
            ):
                continue

            try:
                timestamp = int(timestamp)
                open_price, high, low, close = map(
                    float, (open_price, high, low, close)
                )
                volume = float(volume_value) if volume_value is not None else 0
            except (TypeError, ValueError, OverflowError) as error:
                raise ValueError(
                    f"Yahoo Finance returned invalid bar data for {yahoo_symbol}"
                ) from error

            adjusted_close = _value_at(adjusted_closes, index)
            if adjusted_close is not None and close != 0:
                try:
                    adjusted_close = float(adjusted_close)
                except (TypeError, ValueError, OverflowError) as error:
                    raise ValueError(
                        f"Yahoo Finance returned invalid adjusted close for {yahoo_symbol}"
                    ) from error
                adjustment = adjusted_close / close
                open_price *= adjustment
                high *= adjustment
                low *= adjustment
                close = adjusted_close

            prices.append(
                StockPrice(
                    symbol=symbol,
                    date=datetime.fromtimestamp(timestamp, UTC).date(),
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                )
            )
        return prices


def _yahoo_symbol(symbol: str) -> str:
    """Translate local symbol conventions to Yahoo's chart-symbol conventions."""
    return YAHOO_SYMBOL_ALIASES.get(symbol, symbol.replace(".", "-"))


def _value_at(values: list[Any] | None, index: int) -> Any | None:
    if values is None or index >= len(values):
        return None
    return values[index]
