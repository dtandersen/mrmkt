"""Symbol catalog commands (import/list/label/unlabel)."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared, symbols_app
from mrmkt.ext.alpaca import AlpacaTickerRepository
from mrmkt.usecase.fetch_tickers import FetchTickersResult, FetchTickersUseCase


@symbols_app.command("import")
def import_symbols(
    provider: str = typer.Option(..., "--provider", help="Symbol source (currently: alpaca)"),
) -> None:
    if provider.lower() != "alpaca":
        raise typer.BadParameter("only the 'alpaca' provider is currently supported")

    close_repository: Callable[[], None] | None = None
    try:
        alpaca_client = _shared.create_alpaca_client()
        local_repository, close_repository = _shared.create_local_ticker_repository()
        use_case = FetchTickersUseCase(
            remote=AlpacaTickerRepository(alpaca_client),
            local=local_repository,
        )
        imported_count: list[int] = []
        use_case.result = FetchTickersResult(on_tickers_updated=imported_count.append)
        use_case.execute()
    except Exception as error:
        typer.echo(f"Failed to import symbols from Alpaca: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()

    count = imported_count[0] if imported_count else 0
    typer.echo(f"Imported {count} newly imported symbol{'s' if count != 1 else ''}.")
