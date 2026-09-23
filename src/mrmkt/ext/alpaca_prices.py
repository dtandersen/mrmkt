from datetime import date, datetime, time, timezone
from typing import Any

from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from mrmkt.entity.stock_price import StockPrice


class AlpacaPriceSource:
    """Fetch split- and dividend-adjusted daily stock bars from Alpaca."""

    def __init__(self, client: Any):
        self.client = client

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

        request = StockBarsRequest(
            symbol_or_symbols=normalized_symbols,
            start=datetime.combine(start, time.min, tzinfo=timezone.utc),
            end=datetime.combine(end, time.max, tzinfo=timezone.utc),
            timeframe=TimeFrame(1, TimeFrameUnit("Day")),
            adjustment=Adjustment.ALL,
            feed=DataFeed.IEX,
        )
        response = self.client.get_stock_bars(request)
        bars_by_symbol = response.data if hasattr(response, "data") else response

        return {
            symbol: [
                StockPrice(
                    symbol=symbol,
                    date=bar.timestamp.date(),
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
                for bar in bars_by_symbol.get(symbol, [])
            ]
            for symbol in normalized_symbols
        }
