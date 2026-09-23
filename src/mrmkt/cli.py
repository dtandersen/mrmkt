from collections.abc import Callable
from datetime import date
from pathlib import Path
import re
from urllib.parse import urlsplit

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from psycopg2.pool import SimpleConnectionPool
import typer
import yaml

from mrmkt.common.sql import InsecureSqlGenerator
from mrmkt.common.sqlfinrepo import SqlFinancialRepository
from mrmkt.ext.alpaca import AlpacaTickerRepository
from mrmkt.ext.alpaca_prices import AlpacaPriceSource
from mrmkt.ext.postgres import PostgresSqlClient
from mrmkt.usecase.fetch_tickers import FetchTickersResult, FetchTickersUseCase
from mrmkt.usecase.import_prices import ImportPricesUseCase

app = typer.Typer(no_args_is_help=True, help="MrMkt stock-market tools")
symbols_app = typer.Typer(no_args_is_help=True, help="Manage the local symbol catalog")
prices_app = typer.Typer(no_args_is_help=True, help="Import historical prices")
app.add_typer(symbols_app, name="symbols")
app.add_typer(prices_app, name="prices")


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


def create_local_ticker_repository() -> tuple[SqlFinancialRepository, Callable[[], None]]:
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


def create_alpaca_data_client() -> StockHistoricalDataClient:
    config = yaml.safe_load(Path("alpaca.yaml").read_text())
    return StockHistoricalDataClient(
        api_key=config["key"],
        secret_key=config["secret"],
    )


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


@prices_app.command("import")
def import_prices(
    symbols: list[str] | None = typer.Argument(None, help="Symbols to import"),
    provider: str = typer.Option(..., "--provider", help="Price source (currently: alpaca)"),
    all_symbols: bool = typer.Option(False, "--all", help="Import every locally cataloged symbol"),
    from_date: str = typer.Option(..., "--from", help="First date to include (YYYY-MM-DD)"),
    to_date: str = typer.Option(..., "--to", help="Last date to include (YYYY-MM-DD)"),
) -> None:
    if provider.lower() != "alpaca":
        raise typer.BadParameter("only the 'alpaca' provider is currently supported")
    if all_symbols and symbols:
        raise typer.BadParameter("provide symbols or use --all, not both")
    if not all_symbols and not symbols:
        raise typer.BadParameter("provide one or more symbols or use --all")
    try:
        start_date = date.fromisoformat(from_date)
        end_date = date.fromisoformat(to_date)
    except ValueError as error:
        raise typer.BadParameter("dates must use YYYY-MM-DD format") from error
    if start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    close_repository: Callable[[], None] | None = None
    try:
        local_repository, close_repository = create_local_ticker_repository()
        selected_symbols = (
            [ticker.ticker for ticker in local_repository.get_tickers()]
            if all_symbols
            else symbols or []
        )
        selected_symbols = list(dict.fromkeys(symbol.upper() for symbol in selected_symbols))
        if not selected_symbols:
            typer.echo("No symbols to import.")
            return

        price_source = AlpacaPriceSource(create_alpaca_data_client())
        imported_count = ImportPricesUseCase(price_source, local_repository).execute(
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
        f"Imported {imported_count} new daily bars for "
        f"{len(selected_symbols)} symbol{'s' if len(selected_symbols) != 1 else ''}."
    )


@prices_app.command("list")
def list_prices(
    symbols: list[str] = typer.Argument(..., help="One or more symbols to list"),
    from_date: str | None = typer.Option(None, "--from", help="First date to include (YYYY-MM-DD)"),
    to_date: str | None = typer.Option(None, "--to", help="Last date to include (YYYY-MM-DD)"),
) -> None:
    try:
        start_date = date.fromisoformat(from_date) if from_date is not None else None
        end_date = date.fromisoformat(to_date) if to_date is not None else None
    except ValueError as error:
        raise typer.BadParameter("dates must use YYYY-MM-DD format") from error
    if start_date is not None and end_date is not None and start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    normalized_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols))
    for symbol in normalized_symbols:
        if re.fullmatch(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*", symbol) is None:
            raise typer.BadParameter(f"invalid stock symbol: {symbol}")

    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = create_local_ticker_repository()
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
