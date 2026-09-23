from collections.abc import Callable
from dataclasses import dataclass

from mrmkt.common.sql import Duplicate
from mrmkt.repo.tickers import ReadOnlyTickerRepository, TickerRepository


@dataclass
class FetchTickersResult:
    on_tickers_updated: Callable[[int], None]


class FetchTickersUseCase:
    result: FetchTickersResult | None

    def __init__(self, remote: ReadOnlyTickerRepository, local: TickerRepository):
        self.local = local
        self.remote = remote
        self.result = None

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
