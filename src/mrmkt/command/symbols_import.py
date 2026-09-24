"""Symbol catalog commands (import/list/label/unlabel)."""

from collections.abc import Callable
from dataclasses import dataclass

import typer

from mrmkt.command import _shared, symbols_app
from mrmkt.common.sql import Duplicate
from mrmkt.ext.alpaca import AlpacaTickerRepository
from mrmkt.repo.tickers import ReadOnlyTickerRepository, TickerRepository


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


@dataclass
class FetchTickersResult:
    on_tickers_updated: Callable[[int], None]


class FetchTickersUseCase:
    def __init__(self, remote: ReadOnlyTickerRepository, local: TickerRepository):
        self.local = local
        self.remote = remote
        self.result: FetchTickersResult | None = None

    def execute(self) -> int:
        tickers = self.remote.get_tickers()
        imported_count = 0
        for ticker in tickers:
            try:
                self.local.add_ticker(ticker)
            except Duplicate:
                continue
            imported_count += 1

        if self.result is not None:
            self.result.on_tickers_updated(imported_count)
        return imported_count
