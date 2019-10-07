from mrmkt.repo.tickers import ReadOnlyTickerRepository, TickerRepository


class FetchTickersUseCase:
    def __init__(self, remote: ReadOnlyTickerRepository, local: TickerRepository):
        self.local = local
        self.remote = remote

    def execute(self):
        pass
