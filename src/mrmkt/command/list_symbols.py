"""Stored symbol-list command."""

from dataclasses import dataclass

from mrmkt.command._shared import normalize_tag
from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.ticker import Ticker


@dataclass(frozen=True)
class ListSymbolsRequest:
    tag: str | None = None


@dataclass
class ListSymbolsResult(BaseResult[list[Ticker]]):
    pass


class ListSymbols(Command[ListSymbolsRequest, ListSymbolsResult]):
    """List stored symbols, optionally filtered by tag, in deterministic order."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: ListSymbolsRequest) -> ListSymbolsResult:
        try:
            normalized_tag = (
                normalize_tag(request.tag) if request.tag is not None else None
            )
        except ValueError as error:
            return ListSymbolsResult.invalid_data([str(error)])
        try:
            source_tickers = (
                self.repository.list_tickers_by_tag(normalized_tag)
                if normalized_tag is not None
                else self.repository.get_tickers()
            )
        except Exception as error:
            return ListSymbolsResult.error([f"Failed to list symbols: {error}"])
        return ListSymbolsResult.success(
            sorted(
                source_tickers,
                key=lambda ticker: (ticker.ticker, ticker.exchange, ticker.type),
            )
        )
