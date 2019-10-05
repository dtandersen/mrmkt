from abc import abstractmethod, ABC
from dataclasses import dataclass

from mrmkt.repo.provider import ReadOnlyMarketDataProvider, MarketDataProvider
from mrmkt.usecase.fetch import FinancialLoader
from mrmkt.usecase.price_loader import PriceLoader


class MrMktUseCaseFactory(ABC):
    @abstractmethod
    def fetch_financials(self) -> FinancialLoader:
        pass

    @abstractmethod
    def fetch_prices(self) -> PriceLoader:
        pass


@dataclass
class TestMrMktUseCaseFactory(MrMktUseCaseFactory):
    fingate2: ReadOnlyMarketDataProvider
    findb2: MarketDataProvider

    def fetch_financials(self):
        return FinancialLoader(self.fingate2, self.findb2)

    def fetch_prices(self) -> PriceLoader:
        return PriceLoader(self.fingate2, self.findb2)
