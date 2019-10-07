from mrmkt.common.sql import Duplicate
from mrmkt.repo.tickers import ReadOnlyTickerRepository, TickerRepository


class FetchTickersUseCase:
    def __init__(self, remote: ReadOnlyTickerRepository, local: TickerRepository):
        self.local = local
        self.remote = remote

    def execute(self):
        tickers = self.remote.get_tickers()
        for ticker in tickers:
            try:
                self.local.add_ticker(ticker)
            except Duplicate:
                pass
