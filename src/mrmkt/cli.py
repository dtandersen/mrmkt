from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from alpaca.trading.client import TradingClient
from psycopg2.pool import SimpleConnectionPool
import typer
import yaml

from mrmkt.common.sql import InsecureSqlGenerator
from mrmkt.common.sqlfinrepo import SqlFinancialRepository
from mrmkt.ext.alpaca import AlpacaTickerRepository
from mrmkt.ext.postgres import PostgresSqlClient
from mrmkt.repo.tickers import TickerRepository
from mrmkt.usecase.fetch_tickers import FetchTickersResult, FetchTickersUseCase

app = typer.Typer(no_args_is_help=True, help="MrMkt stock-market tools")
symbols_app = typer.Typer(no_args_is_help=True, help="Manage the local symbol catalog")
app.add_typer(symbols_app, name="symbols")


# These factories are small seams for BDD tests: tests replace them with a fake
# Alpaca client and an in-memory ticker repository.
def create_alpaca_client() -> TradingClient:
    config = yaml.safe_load(Path("alpaca.yaml").read_text())
    endpoint = config["endpoint"].rstrip("/")
    parsed_endpoint = urlsplit(endpoint)
    if parsed_endpoint.hostname != "paper-api.alpaca.markets":
        raise ValueError("Symbol import is restricted to the Alpaca paper endpoint")

    # TradingClient adds its API version itself; the local config includes /v2.
    base_url = endpoint.removesuffix("/v2")
    return TradingClient(
        api_key=config["key"],
        secret_key=config["secret"],
        paper=True,
        url_override=base_url,
    )


def create_local_ticker_repository() -> tuple[TickerRepository, Callable[[], None]]:
    config = yaml.safe_load(Path("dbschema.yml").read_text())
    db_config = config["databases"]["db1"]
    pool = SimpleConnectionPool(
        1,
        5,
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["db"],
    )
    sql_client = PostgresSqlClient(InsecureSqlGenerator(), pool)
    return SqlFinancialRepository(sql_client), pool.closeall


@symbols_app.command("import")
def import_symbols(
    provider: str = typer.Option(..., "--provider", help="Symbol source (currently: alpaca)"),
) -> None:
    if provider.lower() != "alpaca":
        raise typer.BadParameter("only the 'alpaca' provider is currently supported")

    close_repository: Callable[[], None] | None = None
    try:
        alpaca_client = create_alpaca_client()
        local_repository, close_repository = create_local_ticker_repository()
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


@symbols_app.command("list")
def list_symbols() -> None:
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = create_local_ticker_repository()
        tickers = sorted(
            repository.get_tickers(),
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
