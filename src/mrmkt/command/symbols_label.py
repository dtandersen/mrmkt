"""Symbol label command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.symbols_common import (
    TagChangeResult,
    UnknownSymbolsError,
    apply_symbol_tags,
)


@dataclass(frozen=True)
class LabelSymbolsRequest:
    symbols: str
    tag: str


@dataclass
class LabelSymbolsResult(BaseResult[TagChangeResult]):
    pass


class LabelSymbols(Command[LabelSymbolsRequest, LabelSymbolsResult]):
    """Tag stored symbols; reports counts for the CLI to render."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: LabelSymbolsRequest) -> LabelSymbolsResult:
        try:
            outcome = apply_symbol_tags(
                self.repository, request.symbols, request.tag, add=True
            )
        except UnknownSymbolsError as error:
            return LabelSymbolsResult.not_found([str(error)])
        except ValueError as error:
            return LabelSymbolsResult.invalid_data([str(error)])
        return LabelSymbolsResult.success(outcome)
