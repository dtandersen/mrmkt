"""Alpaca latest-quote gateway (outer implementation).

Wraps ``StockHistoricalDataClient.get_stock_latest_quote`` and converts
the SDK model to the gateway ``Quote`` so commands stay SDK-free.
"""

from typing import Any

from alpaca.data.enums import DataFeed
from alpaca.data.requests import StockLatestQuoteRequest

from mrmkt.gateway import Quote, QuoteGateway


class AlpacaQuoteGateway(QuoteGateway):
    """QuoteGateway over the Alpaca data client (IEX by default)."""

    def __init__(self, data_client: Any, feed: str = "iex"):
        self.data_client = data_client
        self.feed = DataFeed.SIP if feed.strip().lower() == "sip" else DataFeed.IEX

    def get_latest_quote(self, symbol: str) -> Quote:
        normalized = symbol.strip().upper()
        response = self.data_client.get_stock_latest_quote(
            StockLatestQuoteRequest(symbol_or_symbols=normalized, feed=self.feed)
        )
        quotes = response.data if hasattr(response, "data") else response
        quote = quotes.get(normalized) if hasattr(quotes, "get") else None
        if quote is None:
            raise KeyError(normalized)
        return Quote(
            symbol=normalized,
            bid=float(quote.bid_price),
            ask=float(quote.ask_price),
            timestamp=quote.timestamp,
        )
