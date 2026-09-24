"""Symbol catalog commands (import/list/label/unlabel)."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared, symbols_app
from mrmkt.command._shared import normalize_tag


@symbols_app.command("list")
def list_symbols(
    tag: str | None = typer.Option(None, "--tag", help="Only show symbols with this tag"),
) -> None:
    normalized_tag = normalize_tag(tag) if tag is not None else None
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        source_tickers = (
            repository.list_tickers_by_tag(normalized_tag)
            if normalized_tag is not None
            else repository.get_tickers()
        )
        tickers = sorted(
            source_tickers,
            key=lambda ticker: (ticker.ticker, ticker.exchange, ticker.type),
        )
    except Exception as error:
        typer.echo(f"Failed to list symbols: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()

    if not tickers:
        typer.echo("No symbols found.")
        return

    typer.echo("SYMBOL | EXCHANGE | TYPE")
    for ticker in tickers:
        typer.echo(f"{ticker.ticker} | {ticker.exchange} | {ticker.type}")
