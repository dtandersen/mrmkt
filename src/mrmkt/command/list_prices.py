"""Stored price-list command."""

import re
from dataclasses import dataclass
from datetime import date

from mrmkt.command._shared import parse_cli_date
from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.stock_price import StockPrice

_SYMBOL_PATTERN = re.compile(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*")


@dataclass(frozen=True)
class ListPricesRequest:
    symbols: list[str]
    from_date: str | None = None
    to_date: str | None = None


@dataclass
class ListPricesResult(BaseResult[list[StockPrice]]):
    pass


class ListPrices(Command[ListPricesRequest, ListPricesResult]):
    """List stored daily bars for symbols in a deterministic order."""

    def __init__(self, repository, clock):
        self.repository = repository
        self.clock = clock

    def execute(self, request: ListPricesRequest) -> ListPricesResult:
        today = self.clock.today()
        try:
            start_date = (
                parse_cli_date(request.from_date, today)
                if request.from_date is not None
                else None
            )
            end_date = (
                parse_cli_date(request.to_date, today)
                if request.to_date is not None
                else today
                if request.from_date is not None
                else None
            )
        except ValueError:
            return ListPricesResult.invalid_data(
                ["dates must be ISO dates, now, or durations such as 7d"]
            )
        if start_date is not None and end_date is not None and start_date > end_date:
            return ListPricesResult.invalid_data(["--from must be on or before --to"])

        try:
            normalized_symbols = list(
                dict.fromkeys(symbol.upper() for symbol in request.symbols)
            )
            for symbol in normalized_symbols:
                if not _SYMBOL_PATTERN.fullmatch(symbol):
                    raise ValueError(f"invalid stock symbol: {symbol}")
        except ValueError as error:
            return ListPricesResult.invalid_data([str(error)])
        price_start = start_date or date.min
        price_end = end_date or date.max
        try:
            prices = [
                price
                for symbol in normalized_symbols
                for price in self.repository.list_prices(symbol, price_start, price_end)
            ]
        except Exception as error:
            return ListPricesResult.error([f"Failed to list prices: {error}"])
        prices.sort(key=lambda price: (price.symbol, price.date))
        return ListPricesResult.success(prices)
