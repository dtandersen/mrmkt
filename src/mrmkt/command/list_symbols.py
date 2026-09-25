"""Stored symbol-list command."""

from mrmkt.command._shared import normalize_tag
from mrmkt.entity.ticker import Ticker


class ListSymbols:
    """List stored symbols, optionally filtered by tag, in deterministic order."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, tag: str | None = None) -> list[Ticker]:
        normalized_tag = normalize_tag(tag) if tag is not None else None
        source_tickers = (
            self.repository.list_tickers_by_tag(normalized_tag)
            if normalized_tag is not None
            else self.repository.get_tickers()
        )
        return sorted(
            source_tickers,
            key=lambda ticker: (ticker.ticker, ticker.exchange, ticker.type),
        )
