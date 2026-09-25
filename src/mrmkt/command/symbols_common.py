"""Shared helpers for symbol-tag commands (no Typer, no repository construction)."""

from dataclasses import dataclass

from mrmkt.command._shared import normalize_symbol, normalize_tag
from mrmkt.common.sql import Duplicate


@dataclass(frozen=True)
class TagChangeResult:
    """Outcome of a label/unlabel run; the CLI renders it verbatim."""

    changed_count: int
    matched_count: int
    unmatched_count: int
    tag: str
    added: bool


class UnknownSymbolsError(ValueError):
    """None of the supplied symbols are in the local ticker catalog."""


def apply_symbol_tags(
    repository, symbols: str, tag: str, add: bool
) -> TagChangeResult:
    """Validate the CSV/tag, apply the change, and report what happened."""
    normalized_symbols = list(
        dict.fromkeys(
            normalize_symbol(symbol) for symbol in symbols.split(",") if symbol.strip()
        )
    )
    if not normalized_symbols:
        raise ValueError("provide at least one comma-separated symbol")
    normalized_tag = normalize_tag(tag)

    tickers_by_symbol: dict[str, list] = {}
    for ticker in repository.get_tickers():
        tickers_by_symbol.setdefault(ticker.ticker, []).append(ticker)

    changed_count = 0
    matched_symbols = set()
    unmatched_symbols = []
    for symbol in normalized_symbols:
        matching = tickers_by_symbol.get(symbol, [])
        if not matching:
            unmatched_symbols.append(symbol)
            continue
        matched_symbols.add(symbol)
        for ticker in matching:
            if add:
                try:
                    repository.add_tag(ticker.ticker, ticker.exchange, normalized_tag)
                except Duplicate:
                    continue
                changed_count += 1
            elif repository.remove_tag(ticker.ticker, ticker.exchange, normalized_tag):
                changed_count += 1

    if not matched_symbols:
        raise UnknownSymbolsError(
            "none of the supplied symbols are in the local ticker catalog"
        )
    return TagChangeResult(
        changed_count=changed_count,
        matched_count=len(matched_symbols),
        unmatched_count=len(unmatched_symbols),
        tag=normalized_tag,
        added=add,
    )
