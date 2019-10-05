from abc import abstractmethod, ABC

from mrmkt.repo.provider import MarketDataProvider, ReadOnlyMarketDataProvider


class MrMktEnvironment(ABC):
    @property
    @abstractmethod
    def local(self) -> MarketDataProvider:
        pass

    @property
    @abstractmethod
    def remote(self) -> ReadOnlyMarketDataProvider:
        pass
