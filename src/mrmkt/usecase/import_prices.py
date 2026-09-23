import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from mrmkt.common.sql import Duplicate
from mrmkt.ext.alpaca_prices import AlpacaPriceSource
from mrmkt.repo.prices import PriceRepository

_SYMBOL_PATTERN = re.compile(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*")


@dataclass
class ImportPricesResult:
    """Outcome of a bounded daily-price import."""

    imported: int = 0
    failed_batches: list[list[str]] = field(default_factory=list)

    @property
    def failed_symbols(self) -> list[str]:
        return [symbol for batch in self.failed_batches for symbol in batch]


class ImportPricesUseCase:
    """Import bounded daily price history from Alpaca into the local store.

    Symbols are fetched in batches. A batch that keeps failing after
    ``max_attempts`` is recorded in ``ImportPricesResult.failed_batches``
    instead of aborting the whole run, so one bad batch does not discard
    thousands of successfully imported bars. Failed batches wait with
    exponential backoff between attempts.
    """

    batch_size = 100

    def __init__(
        self,
        source: AlpacaPriceSource,
        destination: PriceRepository,
        max_attempts: int = 3,
        retry_base_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        on_progress: Callable[[int, int], None] | None = None,
    ):
        self.source = source
        self.destination = destination
        self.max_attempts = max_attempts
        self.retry_base_seconds = retry_base_seconds
        self.sleep = sleep
        self.on_progress = on_progress

    def execute(self, symbols: list[str], start: date, end: date) -> ImportPricesResult:
        if start > end:
            raise ValueError("--from must be on or before --to")

        normalized_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols))
        for symbol in normalized_symbols:
            if _SYMBOL_PATTERN.fullmatch(symbol) is None:
                raise ValueError(f"invalid stock symbol: {symbol}")
        result = ImportPricesResult()
        total = len(normalized_symbols)
        done = 0
        for offset in range(0, total, self.batch_size):
            batch = normalized_symbols[offset : offset + self.batch_size]
            try:
                prices_by_symbol = self._fetch_with_retry(batch, start, end)
            except Exception:
                result.failed_batches.append(batch)
                done += len(batch)
                self._report_progress(done, total)
                continue
            for symbol in batch:
                for price in prices_by_symbol.get(symbol, []):
                    try:
                        self.destination.add_price(price)
                    except Duplicate:
                        continue
                    result.imported += 1
            done += len(batch)
            self._report_progress(done, total)

        return result

    def _fetch_with_retry(
        self, batch: list[str], start: date, end: date
    ) -> dict:
        attempt = 0
        while True:
            try:
                return self.source.get_prices(batch, start, end)
            except Exception:
                attempt += 1
                if attempt >= self.max_attempts:
                    raise
                self.sleep(self.retry_base_seconds * (2 ** (attempt - 1)))

    def _report_progress(self, done: int, total: int) -> None:
        if self.on_progress is not None:
            self.on_progress(done, total)
