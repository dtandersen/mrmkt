"""Price import commands."""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from mrmkt.command._shared import normalize_symbol, normalize_tag, parse_cli_date
from mrmkt.common.sql import Duplicate


@dataclass(frozen=True)
class ImportPricesOutcome:
    """Selected symbols plus the import result; the CLI renders it."""

    selected_symbols: list[str]
    result: "ImportPricesResult"


_SYMBOL_PATTERN = re.compile(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*")


@dataclass
class ImportPricesResult:
    """Outcome of a bounded daily-price import."""

    imported: int = 0
    failed_batches: list[list[str]] = field(default_factory=list)

    @property
    def failed_symbols(self) -> list[str]:
        return [symbol for batch in self.failed_batches for symbol in batch]


class ImportPrices:
    """Import bounded daily price history into the local store.

    Symbols are fetched in batches. A batch that keeps failing after
    ``max_attempts`` is recorded in ``ImportPricesResult.failed_batches``
    instead of aborting the whole run, so one bad batch does not discard
    thousands of successfully imported bars. Failed batches wait with
    exponential backoff between attempts.
    """

    batch_size = 100

    def __init__(
        self,
        price_source,
        local_repository,
        clock,
        on_progress: Callable[[int, int], None] | None = None,
        max_attempts: int = 3,
        retry_base_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.price_source = price_source
        self.local_repository = local_repository
        self.clock = clock
        self.on_progress = on_progress
        self.max_attempts = max_attempts
        self.retry_base_seconds = retry_base_seconds
        self.sleep = sleep

    def execute(
        self,
        provider: str,
        symbols: list[str] | None,
        all_symbols: bool,
        tag: str | None,
        from_date: str,
        to_date: str | None,
    ) -> ImportPricesOutcome:
        if provider.lower() != "alpaca":
            raise ValueError("only the 'alpaca' provider is currently supported")
        selector_count = sum((bool(symbols), all_symbols, tag is not None))
        if selector_count != 1:
            raise ValueError("provide symbols, --all, or --tag")
        normalized_tag = normalize_tag(tag) if tag is not None else None
        today = self.clock.today()
        try:
            start_date = parse_cli_date(from_date, today)
            end_date = parse_cli_date(to_date, today) if to_date is not None else today
        except ValueError as error:
            raise ValueError(
                "dates must be ISO dates, now, or durations such as 180d"
            ) from error
        if start_date > end_date:
            raise ValueError("--from must be on or before --to")

        if normalized_tag is not None:
            selected_symbols = self.local_repository.get_symbols_by_tag(normalized_tag)
        elif all_symbols:
            selected_symbols = [
                ticker.ticker for ticker in self.local_repository.get_tickers()
            ]
        else:
            selected_symbols = list(symbols or [])
        try:
            selected_symbols = list(
                dict.fromkeys(normalize_symbol(symbol) for symbol in selected_symbols)
            )
        except ValueError as error:
            # Stored or supplied symbols that fail normalization are a data
            # problem, reported through the generic failure path like before.
            raise RuntimeError(str(error)) from error
        if not selected_symbols:
            return ImportPricesOutcome(
                selected_symbols=[], result=ImportPricesResult()
            )
        result = self._import_batches(selected_symbols, start_date, end_date)
        return ImportPricesOutcome(
            selected_symbols=selected_symbols, result=result
        )

    def _import_batches(
        self, symbols: list[str], start: date, end: date
    ) -> ImportPricesResult:
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
                        self.local_repository.add_price(price)
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
                return self.price_source.get_prices(batch, start, end)
            except Exception:
                attempt += 1
                if attempt >= self.max_attempts:
                    raise
                self.sleep(self.retry_base_seconds * (2 ** (attempt - 1)))

    def _report_progress(self, done: int, total: int) -> None:
        if self.on_progress is not None:
            self.on_progress(done, total)
