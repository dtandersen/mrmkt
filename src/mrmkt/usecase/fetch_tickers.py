from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Optional

from mrmkt.common.sql import Duplicate
from mrmkt.repo.tickers import ReadOnlyTickerRepository, TickerRepository


@dataclass
class FetchTickersResult:
    on_tickers_updated: any


class FetchTickersUseCase:
    result: Optional[FetchTickersResult]

    def __init__(self, remote: ReadOnlyTickerRepository, local: TickerRepository):
        self.local = local
        self.remote = remote
        self.result = None

    def execute(self):
        tickers = self.remote.get_tickers()
        count = 0
        for ticker in tickers:
            try:
                self.local.add_ticker(ticker)
            except Duplicate:
                pass
            count = count + 1

        self.result.on_tickers_updated(count)
