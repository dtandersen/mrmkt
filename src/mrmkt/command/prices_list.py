"""Price commands (import/list/freshness)."""

import re
from collections.abc import Callable
from datetime import date

import typer

from mrmkt.command import _shared, prices_app
from mrmkt.command._shared import parse_cli_date


@prices_app.command("list")
def list_prices(
    symbols: list[str] = typer.Argument(..., help="One or more symbols to list"),
    from_date: str | None = typer.Option(None, "--from", help="Start date (ISO date or duration such as 7d)"),
    to_date: str | None = typer.Option(None, "--to", help="End date (defaults to today when --from is used)"),
) -> None:
    today = _shared.create_clock().today()
    try:
        start_date = parse_cli_date(from_date, today) if from_date is not None else None
        end_date = (
            parse_cli_date(to_date, today)
            if to_date is not None
            else today if from_date is not None else None
        )
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 7d") from error
    if start_date is not None and end_date is not None and start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    normalized_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols))
    for symbol in normalized_symbols:
        if re.fullmatch(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*", symbol) is None:
            raise typer.BadParameter(f"invalid stock symbol: {symbol}")

    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        price_start = start_date or date.min
        price_end = end_date or date.max
        prices = [
            price
            for symbol in normalized_symbols
            for price in repository.list_prices(symbol, price_start, price_end)
        ]
    except Exception as error:
        typer.echo(f"Failed to list prices: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()

    prices.sort(key=lambda price: (price.symbol, price.date))
    if not prices:
        typer.echo("No prices found.")
        return

    typer.echo("SYMBOL | DATE | OPEN | HIGH | LOW | CLOSE | VOLUME")
    for price in prices:
        typer.echo(
            f"{price.symbol} | {price.date.isoformat()} | {price.open:g} | "
            f"{price.high:g} | {price.low:g} | {price.close:g} | {price.volume:g}"
        )
