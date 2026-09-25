"""Symbol import commands."""

from collections.abc import Callable
from dataclasses import dataclass

from mrmkt.common.sql import Duplicate
from mrmkt.repo.tickers import ReadOnlyTickerRepository, TickerRepository


@dataclass
class FetchTickersResult:
    on_tickers_updated: Callable[[int], None]


class FetchTickersUseCase:
    def __init__(self, remote: ReadOnlyTickerRepository, local: TickerRepository):
        self.local = local
        self.remote = remote
        self.result: FetchTickersResult | None = None

    def execute(self) -> int:
        tickers = self.remote.get_tickers()
        imported_count = 0
        for ticker in tickers:
            try:
                self.local.add_ticker(ticker)
            except Duplicate:
                continue
            imported_count += 1

        if self.result is not None:
            self.result.on_tickers_updated(imported_count)
        return imported_count


class ImportSymbols:
    """Import the remote symbol catalog into the local repository."""

    def __init__(self, remote: ReadOnlyTickerRepository, local: TickerRepository):
        self.remote = remote
        self.local = local

    def execute(self, provider: str) -> int:
        if provider.lower() != "alpaca":
            raise ValueError("only the 'alpaca' provider is currently supported")
        use_case = FetchTickersUseCase(remote=self.remote, local=self.local)
        imported_count: list[int] = []
        use_case.result = FetchTickersResult(
            on_tickers_updated=imported_count.append
        )
        use_case.execute()
        return imported_count[0] if imported_count else 0
