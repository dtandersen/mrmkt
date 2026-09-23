from datetime import date

from mrmkt.common.sql import Duplicate
from mrmkt.ext.alpaca_prices import AlpacaPriceSource
from mrmkt.repo.prices import PriceRepository


class ImportPricesUseCase:
    """Import bounded daily price history from Alpaca into the local store."""

    batch_size = 100

    def __init__(self, source: AlpacaPriceSource, destination: PriceRepository):
        self.source = source
        self.destination = destination

    def execute(self, symbols: list[str], start: date, end: date) -> int:
        if start > end:
            raise ValueError("--from must be on or before --to")

        normalized_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols))
        imported_count = 0
        for offset in range(0, len(normalized_symbols), self.batch_size):
            batch = normalized_symbols[offset : offset + self.batch_size]
            prices_by_symbol = self.source.get_prices(batch, start, end)
            for symbol in batch:
                for price in prices_by_symbol.get(symbol, []):
                    try:
                        self.destination.add_price(price)
                    except Duplicate:
                        continue
                    imported_count += 1

        return imported_count
