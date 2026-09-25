"""Stored price-list command."""

import re
from datetime import date

from mrmkt.command._shared import parse_cli_date
from mrmkt.entity.stock_price import StockPrice

_SYMBOL_PATTERN = re.compile(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*")


class ListPrices:
    """List stored daily bars for symbols in a deterministic order."""

    def __init__(self, repository, clock):
        self.repository = repository
        self.clock = clock

    def execute(
        self,
        symbols: list[str],
        from_date: str | None,
        to_date: str | None,
    ) -> list[StockPrice]:
        today = self.clock.today()
        try:
            start_date = (
                parse_cli_date(from_date, today) if from_date is not None else None
            )
            end_date = (
                parse_cli_date(to_date, today)
                if to_date is not None
                else today if from_date is not None else None
            )
        except ValueError as error:
            raise ValueError(
                "dates must be ISO dates, now, or durations such as 7d"
            ) from error
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError("--from must be on or before --to")

        normalized_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols))
        for symbol in normalized_symbols:
            if not _SYMBOL_PATTERN.fullmatch(symbol):
                raise ValueError(f"invalid stock symbol: {symbol}")
        price_start = start_date or date.min
        price_end = end_date or date.max
        prices = [
            price
            for symbol in normalized_symbols
            for price in self.repository.list_prices(symbol, price_start, price_end)
        ]
        prices.sort(key=lambda price: (price.symbol, price.date))
        return prices
