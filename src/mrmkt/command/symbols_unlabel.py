"""Symbol unlabel command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.symbols_common import (
    TagChangeResult,
    UnknownSymbolsError,
    apply_symbol_tags,
)


@dataclass(frozen=True)
class UnlabelSymbolsRequest:
    symbols: str
    tag: str


@dataclass
class UnlabelSymbolsResult(BaseResult[TagChangeResult]):
    pass


class UnlabelSymbols(Command[UnlabelSymbolsRequest, UnlabelSymbolsResult]):
    """Untag stored symbols; reports counts for the CLI to render."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: UnlabelSymbolsRequest) -> UnlabelSymbolsResult:
        try:
            outcome = apply_symbol_tags(
                self.repository, request.symbols, request.tag, add=False
            )
        except UnknownSymbolsError as error:
            return UnlabelSymbolsResult.not_found([str(error)])
        except ValueError as error:
            return UnlabelSymbolsResult.invalid_data([str(error)])
        return UnlabelSymbolsResult.success(outcome)
