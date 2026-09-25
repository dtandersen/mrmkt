"""Symbol import command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.common.sql import Duplicate
from mrmkt.repo.tickers import ReadOnlyTickerRepository, TickerRepository


@dataclass(frozen=True)
class ImportSymbolsRequest:
    provider: str


@dataclass
class ImportSymbolsResult(BaseResult[int]):
    pass


class ImportSymbols(Command[ImportSymbolsRequest, ImportSymbolsResult]):
    """Import the remote symbol catalog into the local repository."""

    def __init__(self, remote: ReadOnlyTickerRepository, local: TickerRepository):
        self.remote = remote
        self.local = local

    def execute(self, request: ImportSymbolsRequest) -> ImportSymbolsResult:
        if request.provider.lower() != "alpaca":
            return ImportSymbolsResult.invalid_data(
                ["only the 'alpaca' provider is currently supported"]
            )
        imported_count = 0
        try:
            remote_tickers = self.remote.get_tickers()
        except Exception as error:
            return ImportSymbolsResult.error([str(error)])
        for ticker in remote_tickers:
            try:
                self.local.add_ticker(ticker)
            except Duplicate:
                continue
            imported_count += 1
        return ImportSymbolsResult.success(imported_count)
