from mrmkt.common.clock import ClockStub
from mrmkt.common.environment import MrMktEnvironment
from mrmkt.ext.backend import InMemoryBackend
from mrmkt.repo.provider import MarketDataProvider


class TestMarketDataProvider(MarketDataProvider):
    def __init__(self, repo: InMemoryBackend):
        super().__init__(repo, repo, repo)
        self.repo = repo


class TestEnvironment(MrMktEnvironment):
    def __init__(self):
        local = InMemoryBackend()
        remote = InMemoryBackend()
        self._local = TestMarketDataProvider(local)
        self._remote = TestMarketDataProvider(remote)
        self._clock = ClockStub()

    @property
    def local(self) -> TestMarketDataProvider:
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
