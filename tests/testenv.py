from mrmkt.common.clock import ClockStub
from mrmkt.common.environment import MrMktEnvironment
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.common.testfinrepo import FinancialTestRepository
from mrmkt.repo.provider import MarketDataProvider


class TestMarketDataProvider(MarketDataProvider):
    def __init__(self, repo: FinancialTestRepository):
        super().__init__(repo, repo, repo)
        self.repo = repo

    def add_nvidia_financials(self):
        self.repo.add_nvidia_financials()

    def add_apple_financials(self):
        self.repo.add_apple_financials()

    def add_google_financials(self):
        self.repo.add_google_financials()

    def with_spy(self):
        self.repo.with_spy()

    def add_netflix_financials(self):
        self.repo.add_netflix_financials()


class TestEnvironment(MrMktEnvironment):
    def __init__(self):
        # td = FinancialTestRepository()
        local = InMemoryFinancialRepository()
        remote = FinancialTestRepository()
        self._local = MarketDataProvider(financials=local, prices=local, tickers=local)
        self._remote = TestMarketDataProvider(remote)
        # self._test_data = TestMarketDataProvider(td)
        self._clock = ClockStub()

    @property
    def local(self) -> MarketDataProvider:
        return self._local

    @property
    def remote(self) -> TestMarketDataProvider:
        return self._remote

    @property
    def clock(self) -> ClockStub:
        return self._clock

    # @property
    # def test_data(self) -> TestMarketDataProvider:
    #     return self._test_data
