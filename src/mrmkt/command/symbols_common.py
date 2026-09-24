"""Symbol catalog commands (import/list/label/unlabel)."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared
from mrmkt.command._shared import normalize_symbol, normalize_tag
from mrmkt.common.sql import Duplicate


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
        repository, close_repository = _shared.create_local_ticker_repository()
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
