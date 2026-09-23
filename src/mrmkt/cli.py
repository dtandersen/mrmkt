import re
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import typer
import yaml
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
import pandas as pd
from psycopg2.pool import SimpleConnectionPool

from mrmkt.common.clock import Clock, WallClock
from mrmkt.common.sql import Duplicate, InsecureSqlGenerator
from mrmkt.common.sqlfinrepo import SqlFinancialRepository
from mrmkt.ext.alpaca import AlpacaTickerRepository
from mrmkt.ext.alpaca_prices import AlpacaPriceSource
from mrmkt.ext.postgres import PostgresSqlClient
from mrmkt.backtest.signals import BacktestParams
from mrmkt.backtest.strategy import BuyRedStrategy, SmaCrossStrategy, StrategyRunner
from mrmkt.indicator.risk_range import RiskRange, risk_range_series
from mrmkt.indicator.sma import sma
from mrmkt.indicator.volatility import (
    volatility,
    volatility_of_volatility,
    volatility_of_volatility_percentile,
    volatility_percentile,
)
from mrmkt.usecase.fetch_tickers import FetchTickersResult, FetchTickersUseCase
from mrmkt.usecase.import_prices import ImportPricesUseCase

app = typer.Typer(no_args_is_help=True, help="MrMkt stock-market tools")
symbols_app = typer.Typer(no_args_is_help=True, help="Manage the local symbol catalog")
prices_app = typer.Typer(no_args_is_help=True, help="Import and list historical prices")
indicators_app = typer.Typer(no_args_is_help=True, help="Calculate indicators over stored prices")
backtest_app = typer.Typer(no_args_is_help=True, help="Backtest signal portfolios over stored prices")
app.add_typer(symbols_app, name="symbols")
app.add_typer(prices_app, name="prices")
app.add_typer(indicators_app, name="indicators")
app.add_typer(backtest_app, name="backtest")


def create_clock() -> Clock:
    return WallClock()


def parse_cli_date(value: str, today: date) -> date:
    normalized = value.strip().lower()
    if normalized in {"now", "today"}:
        return today

    relative = re.fullmatch(r"(\d+)\s*(?:d|days?)(?:\s+ago)?", normalized)
    if relative:
        try:
            days = int(relative.group(1))
        except ValueError as error:
            raise ValueError("invalid relative date") from error
        return today - timedelta(days=days)

    return date.fromisoformat(normalized)


def normalize_tag(tag: str) -> str:
    normalized = tag.strip().lower()
    if re.fullmatch(r"[a-z0-9][a-z0-9_-]*", normalized) is None:
        raise typer.BadParameter("tags must start with a letter or number and contain only letters, numbers, '_' or '-'")
    return normalized


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if re.fullmatch(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*", normalized) is None:
        raise typer.BadParameter(f"invalid stock symbol: {symbol}")
    return normalized


def _run_indicator_series(
    symbol: str,
    from_date: str | None,
    to_date: str | None,
    indicator_name: str,
    calculate: Callable[[list[float]], list[float]],
    first_result_index: int,
) -> None:
    normalized_symbol = symbol.upper()
    if re.fullmatch(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*", normalized_symbol) is None:
        raise typer.BadParameter(f"invalid stock symbol: {symbol}")

    today = create_clock().today()
    try:
        start_date = parse_cli_date(from_date, today) if from_date is not None else None
        end_date = parse_cli_date(to_date, today) if to_date is not None else today
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    if start_date is not None and start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = create_local_ticker_repository()
        prices = sorted(
            repository.list_prices(normalized_symbol, date.min, end_date),
            key=lambda price: price.date,
        )
        values = calculate([price.close for price in prices])
    except Exception as error:
        typer.echo(f"Failed to calculate {indicator_name}: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()

    aligned_prices = prices[first_result_index : first_result_index + len(values)]
    rows = [
        (price, value)
        for price, value in zip(aligned_prices, values, strict=True)
        if start_date is None or price.date >= start_date
    ]
    if not rows:
        typer.echo("No indicator values available.")
        return

    typer.echo(f"DATE | CLOSE | {indicator_name}")
    for price, value in rows:
        typer.echo(f"{price.date.isoformat()} | {price.close:g} | {value:g}")


def _run_indicator_pair_series(
    symbol: str,
    from_date: str | None,
    to_date: str | None,
    low_name: str,
    high_name: str,
    calculate: Callable[[list[float]], list[RiskRange]],
    first_result_index: int,
) -> None:
    normalized_symbol = symbol.upper()
    if re.fullmatch(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*", normalized_symbol) is None:
        raise typer.BadParameter(f"invalid stock symbol: {symbol}")

    today = create_clock().today()
    try:
        start_date = parse_cli_date(from_date, today) if from_date is not None else None
        end_date = parse_cli_date(to_date, today) if to_date is not None else today
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    if start_date is not None and start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = create_local_ticker_repository()
        prices = sorted(
            repository.list_prices(normalized_symbol, date.min, end_date),
            key=lambda price: price.date,
        )
        values = calculate([price.close for price in prices])
    except Exception as error:
        typer.echo(f"Failed to calculate {low_name}/{high_name}: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()

    aligned_prices = prices[first_result_index : first_result_index + len(values)]
    rows = [
        (price, value)
        for price, value in zip(aligned_prices, values, strict=True)
        if start_date is None or price.date >= start_date
    ]
    if not rows:
        typer.echo("No indicator values available.")
        return

    typer.echo(f"DATE | CLOSE | {low_name} | {high_name}")
    for price, value in rows:
        typer.echo(f"{price.date.isoformat()} | {price.close:g} | {value.low:g} | {value.high:g}")


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
def list_symbols(
    tag: str | None = typer.Option(None, "--tag", help="Only show symbols with this tag"),
) -> None:
    normalized_tag = normalize_tag(tag) if tag is not None else None
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = create_local_ticker_repository()
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


@symbols_app.command("label")
def label_symbols(symbols: str, tag: str) -> None:
    _change_symbol_tags(symbols, tag, add=True)


@symbols_app.command("unlabel")
def unlabel_symbols(symbols: str, tag: str) -> None:
    _change_symbol_tags(symbols, tag, add=False)


def _change_symbol_tags(symbols: str, tag: str, add: bool) -> None:
    normalized_symbols = list(
        dict.fromkeys(normalize_symbol(symbol) for symbol in symbols.split(",") if symbol.strip())
    )
    if not normalized_symbols:
        raise typer.BadParameter("provide at least one comma-separated symbol")
    tag = normalize_tag(tag)

    close_repository: Callable[[], None] | None = None
    changed_count = 0
    matched_symbols = set()
    unmatched_symbols = []
    try:
        repository, close_repository = create_local_ticker_repository()
        tickers_by_symbol: dict[str, list] = {}
        for ticker in repository.get_tickers():
            tickers_by_symbol.setdefault(ticker.ticker, []).append(ticker)

        for symbol in normalized_symbols:
            matching = tickers_by_symbol.get(symbol, [])
            if not matching:
                unmatched_symbols.append(symbol)
                continue
            matched_symbols.add(symbol)
            for ticker in matching:
                if add:
                    try:
                        repository.add_tag(ticker.ticker, ticker.exchange, tag)
                    except Duplicate:
                        continue
                    changed_count += 1
                elif repository.remove_tag(ticker.ticker, ticker.exchange, tag):
                    changed_count += 1
    except Exception as error:
        typer.echo(f"Failed to {'label' if add else 'unlabel'} symbols: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()

    if not matched_symbols:
        raise typer.BadParameter("none of the supplied symbols are in the local ticker catalog")
    action = "Added" if add else "Removed"
    typer.echo(
        f"{action} {changed_count} '{tag}' tag assignment"
        f"{'s' if changed_count != 1 else ''} for {len(matched_symbols)} symbols."
    )
    if unmatched_symbols:
        typer.echo(f"Skipped {len(unmatched_symbols)} symbols not in the local ticker catalog.", err=True)


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
    today = create_clock().today()
    try:
        start_date = parse_cli_date(from_date, today)
        end_date = parse_cli_date(to_date, today) if to_date is not None else today
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    if start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    close_repository: Callable[[], None] | None = None
    try:
        local_repository, close_repository = create_local_ticker_repository()
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

        price_source = AlpacaPriceSource(create_alpaca_data_client())

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


@prices_app.command("list")
def list_prices(
    symbols: list[str] = typer.Argument(..., help="One or more symbols to list"),
    from_date: str | None = typer.Option(None, "--from", help="Start date (ISO date or duration such as 7d)"),
    to_date: str | None = typer.Option(None, "--to", help="End date (defaults to today when --from is used)"),
) -> None:
    today = create_clock().today()
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


@indicators_app.command("sma")
def calculate_sma(
    symbol: str,
    period: int = typer.Option(..., min=1, help="Number of daily bars"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if period < 1:
        raise typer.BadParameter("period must be positive")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"SMA_{period}D",
        lambda prices: sma(prices, period),
        period - 1,
    )


@indicators_app.command("volatility")
def calculate_volatility(
    symbol: str,
    period: int = typer.Option(..., min=2, help="Number of daily returns"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if period < 2:
        raise typer.BadParameter("period must be at least 2")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"VOL_{period}D",
        lambda prices: volatility(prices, period),
        period,
    )


@indicators_app.command("vol-of-vol")
def calculate_volatility_of_volatility(
    symbol: str,
    volatility_period: int = typer.Option(..., "--vol-period", min=2),
    vol_of_vol_period: int = typer.Option(..., "--vov-period", min=2),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if volatility_period < 2 or vol_of_vol_period < 2:
        raise typer.BadParameter("both volatility periods must be at least 2")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"VOV_{volatility_period}D_{vol_of_vol_period}D",
        lambda prices: volatility_of_volatility(
            prices,
            volatility_period,
            vol_of_vol_period,
        ),
        volatility_period + vol_of_vol_period,
    )


@indicators_app.command("volatility-percentile")
def calculate_volatility_percentile(
    symbol: str,
    period: int = typer.Option(..., min=2, help="Rolling return window"),
    lookback: int = typer.Option(252, min=1, help="Prior volatility values used for ranking"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if period < 2 or lookback < 1:
        raise typer.BadParameter("period must be at least 2 and lookback must be positive")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"VOL_{period}D_PCTL_{lookback}D",
        lambda prices: volatility_percentile(prices, period, lookback),
        period + lookback,
    )


@indicators_app.command("vol-of-vol-percentile")
def calculate_volatility_of_volatility_percentile(
    symbol: str,
    volatility_period: int = typer.Option(..., "--vol-period", min=2),
    vol_of_vol_period: int = typer.Option(..., "--vov-period", min=2),
    lookback: int = typer.Option(252, min=1, help="Prior vol-of-vol values used for ranking"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if volatility_period < 2 or vol_of_vol_period < 2 or lookback < 1:
        raise typer.BadParameter("volatility periods must be at least 2 and lookback must be positive")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"VOV_{volatility_period}D_{vol_of_vol_period}D_PCTL_{lookback}D",
        lambda prices: volatility_of_volatility_percentile(
            prices,
            volatility_period,
            vol_of_vol_period,
            lookback,
        ),
        volatility_period + vol_of_vol_period + lookback,
    )


@indicators_app.command("risk-range")
def calculate_risk_range(
    symbol: str,
    horizon: int = typer.Option(15, min=1, help="Range horizon in trading days (15 = TRADE, 63 = TREND)"),
    volatility_period: int = typer.Option(21, "--vol-period", min=2),
    width: float = typer.Option(0.5, help="Range half-width in vol-scaled units"),
    anchor_period: int = typer.Option(5, "--anchor-period", min=1, help="Trailing mean the range is centered on"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if width <= 0:
        raise typer.BadParameter("width must be positive")
    _run_indicator_pair_series(
        symbol,
        from_date,
        to_date,
        f"RR_{horizon}D_LRR",
        f"RR_{horizon}D_TRR",
        lambda prices: risk_range_series(
            prices,
            horizon,
            vol_period=volatility_period,
            width=width,
            anchor_period=anchor_period,
        ),
        volatility_period,
    )


@backtest_app.command("run")
def run_backtest(
    symbols: list[str] | None = typer.Argument(None, help="Symbols to include"),
    all_symbols: bool = typer.Option(False, "--all", help="Include every locally cataloged symbol"),
    tags: list[str] | None = typer.Option(None, "--tag", help="Include symbols with this tag (repeatable)"),
    from_date: str | None = typer.Option(None, "--from", help="Test window start (defaults to auto warm-up)"),
    to_date: str | None = typer.Option(None, "--to", help="Test window end (defaults to today)"),
    width: float = typer.Option(0.5, help="Risk range half-width in vol-scaled units"),
    use_vov: bool = typer.Option(True, help="Require compressed vol-of-vol for entries"),
    strategy_name: str = typer.Option("buy-red", "--strategy", help="Strategy: buy-red or sma-cross"),
    fast_period: int = typer.Option(50, "--fast-period", help="Fast SMA period (sma-cross only)"),
    slow_period: int = typer.Option(200, "--slow-period", help="Slow SMA period (sma-cross only)"),
    size_pct: float = typer.Option(2.0, help="Percent of equity per position"),
    stop: float = typer.Option(0.08, help="Stop-loss fraction"),
    chunk_size: int = typer.Option(250, "--chunk-size", help="Symbols loaded and simulated per chunk"),
) -> None:
    """Backtest long-only buy-red-in-uptrend signals with vectorbt."""
    selector_count = sum((bool(symbols), all_symbols, bool(tags)))
    if selector_count != 1:
        raise typer.BadParameter("provide symbols, --all, or --tag")
    if width <= 0:
        raise typer.BadParameter("width must be positive")
    if not 0 < size_pct <= 100:
        raise typer.BadParameter("size_pct must be between 0 and 100")
    if not 0 < stop < 1:
        raise typer.BadParameter("stop must be between 0 and 1")
    if chunk_size < 1:
        raise typer.BadParameter("chunk-size must be at least 1")

    today = create_clock().today()
    try:
        start_date = parse_cli_date(from_date, today) if from_date is not None else None
        end_date = parse_cli_date(to_date, today) if to_date is not None else today
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    if start_date is not None and start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = create_local_ticker_repository()
        if tags:
            selected = sorted(
                {s for tag in tags for s in repository.get_symbols_by_tag(normalize_tag(tag))}
            )
        elif all_symbols:
            selected = sorted({ticker.ticker for ticker in repository.get_tickers()})
        else:
            selected = [normalize_symbol(symbol) for symbol in (symbols or [])]
        if not selected:
            typer.echo("No symbols to backtest.")
            return

        chunks = []
        union_idx: pd.DatetimeIndex = pd.DatetimeIndex([])
        for offset in range(0, len(selected), chunk_size):
            closes, highs, lows = {}, {}, {}
            bars_by_symbol: dict = {}
            for price in repository.list_prices_for_symbols(
                selected[offset : offset + chunk_size], date.min, end_date
            ):
                bars_by_symbol.setdefault(price.symbol, []).append(price)
            for symbol, bars in bars_by_symbol.items():
                if len(bars) < 360:
                    continue
                index = pd.DatetimeIndex([price.date for price in bars])
                closes[symbol] = pd.Series([price.close for price in bars], index=index)
                highs[symbol] = pd.Series([price.high for price in bars], index=index)
                lows[symbol] = pd.Series([price.low for price in bars], index=index)
            if not closes:
                continue
            chunk_close = pd.DataFrame(closes).sort_index()
            chunks.append(
                (
                    chunk_close,
                    pd.DataFrame(highs).sort_index().reindex_like(chunk_close),
                    pd.DataFrame(lows).sort_index().reindex_like(chunk_close),
                )
            )
            union_idx = pd.DatetimeIndex(union_idx.union(chunk_close.index))
        if not chunks:
            typer.echo("No symbols with enough history to backtest.")
            return
        n_symbols = sum(frame[0].shape[1] for frame in chunks)

        params = BacktestParams(width=width, use_vov=use_vov)
        runner = StrategyRunner(size_pct=size_pct, stop=stop)
        if strategy_name == "sma-cross":
            strategy = SmaCrossStrategy(
                fast_period=fast_period,
                slow_period=slow_period,
            )
        elif strategy_name == "buy-red":
            strategy = BuyRedStrategy(params=params)
        else:
            raise typer.BadParameter("strategy must be buy-red or sma-cross")
        start: date = start_date if start_date is not None else union_idx.date[300]
        result = runner.run_chunked(strategy, chunks, start=start)
    except Exception as error:
        typer.echo(f"Failed to run backtest: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()

    if result.n_trades == 0:
        typer.echo("No trades generated in the test window.")
        return
    typer.echo(f"Symbols: {n_symbols}  Test window: {start} to {end_date}")
    typer.echo(f"Trades: {result.n_trades}  Win rate: {result.win_rate:.1%}")
    typer.echo(f"Avg win: {result.avg_win:+.2%}  Avg loss: {result.avg_loss:+.2%}")
    typer.echo(f"Expectancy: {result.expectancy:+.3%}  Profit factor: {result.profit_factor:.2f}")
    typer.echo(f"Avg hold: {result.avg_hold_days:.1f}d  Exposure: {result.exposure:.1%}")
    typer.echo(
        f"CAGR: {result.cagr:+.1%}  Sharpe: {result.sharpe:.2f}  Max DD: {result.max_drawdown:.1%}"
    )
