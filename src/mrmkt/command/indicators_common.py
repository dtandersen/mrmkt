"""Indicator calculation commands."""

import re
from collections.abc import Callable
from datetime import date

import typer

from mrmkt.command import _shared
from mrmkt.command._shared import parse_cli_date
from mrmkt.indicator.risk_range import RiskRange


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

    today = _shared.create_clock().today()
    try:
        start_date = parse_cli_date(from_date, today) if from_date is not None else None
        end_date = parse_cli_date(to_date, today) if to_date is not None else today
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    if start_date is not None and start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
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

    today = _shared.create_clock().today()
    try:
        start_date = parse_cli_date(from_date, today) if from_date is not None else None
        end_date = parse_cli_date(to_date, today) if to_date is not None else today
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    if start_date is not None and start_date > end_date:
        raise typer.BadParameter("--from must be on or before --to")

    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
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
