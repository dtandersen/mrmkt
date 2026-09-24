"""Price commands (import/list/freshness)."""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

import typer

from mrmkt.command import _shared, prices_app
from mrmkt.command._shared import normalize_symbol, normalize_tag, parse_cli_date
from mrmkt.common.sql import Duplicate
from mrmkt.ext.alpaca_prices import AlpacaPriceSource
from mrmkt.repo.prices import PriceRepository


@prices_app.command("import")
def import_prices(
    symbols: list[str] | None = typer.Argument(None, help="Symbols to import"),
    provider: str = typer.Option(..., "--provider", help="Price source (currently: alpaca)"),
    all_symbols: bool = typer.Option(False, "--all", help="Import every locally cataloged symbol"),
    tag: str | None = typer.Option(None, "--tag", help="Import symbols with this tag"),
    from_date: str = typer.Option(..., "--from", help="Start date (YYYY-MM-DD or duration such as 180d)"),
    to_date: str | None = typer.Option(None, "--to", help="End date (defaults to today)"),
) -> None:
    if provider.lower() != "alpaca":
        raise typer.BadParameter("only the 'alpaca' provider is currently supported")
    selector_count = sum((bool(symbols), all_symbols, tag is not None))
    if selector_count != 1:
        raise typer.BadParameter("provide symbols, --all, or --tag")
    normalized_tag = normalize_tag(tag) if tag is not None else None
    today = _shared.create_clock().today()
    try:
        start_date = parse_cli_date(from_date, today)
        end_date = parse_cli_date(to_date, today) if to_date is not None else today
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    if start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    close_repository: Callable[[], None] | None = None
    try:
        local_repository, close_repository = _shared.create_local_ticker_repository()
        if normalized_tag is not None:
            selected_symbols = local_repository.get_symbols_by_tag(normalized_tag)
        elif all_symbols:
            selected_symbols = [ticker.ticker for ticker in local_repository.get_tickers()]
        else:
            selected_symbols = symbols or []
        selected_symbols = list(dict.fromkeys(normalize_symbol(symbol) for symbol in selected_symbols))
        if not selected_symbols:
            typer.echo("No symbols to import.")
            return

        price_source = AlpacaPriceSource(_shared.create_alpaca_data_client())

        def report_progress(done: int, total: int) -> None:
            typer.echo(f"Imported prices for {done}/{total} symbols...", err=True)

        result = ImportPricesUseCase(
            price_source,
            local_repository,
            on_progress=report_progress,
        ).execute(
            selected_symbols,
            start_date,
            end_date,
        )
    except Exception as error:
        typer.echo(f"Failed to import prices from Alpaca: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()

    typer.echo(
        f"Imported {result.imported} new daily bar{'s' if result.imported != 1 else ''} for "
        f"{len(selected_symbols)} symbol{'s' if len(selected_symbols) != 1 else ''}."
    )
    if result.failed_batches:
        for batch in result.failed_batches:
            typer.echo(
                f"Failed to import prices for: {', '.join(batch)}",
                err=True,
            )
        raise typer.Exit(code=1)


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
