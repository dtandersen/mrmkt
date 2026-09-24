"""Price commands (import/list/freshness)."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared, prices_app
from mrmkt.command._shared import normalize_symbol, normalize_tag, parse_cli_date
from mrmkt.ext.alpaca_prices import AlpacaPriceSource
from mrmkt.usecase.import_prices import ImportPricesUseCase


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
