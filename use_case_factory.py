from abc import abstractmethod, ABC
from dataclasses import dataclass

from mrmkt.usecase.fetch import FinancialLoader
from mrmkt.usecase.price_loader import PriceLoader
from tests.testenv import MrMktEnvironment


class MrMktUseCaseFactory(ABC):
    @abstractmethod
    def fetch_financials(self) -> FinancialLoader:
        pass

    @abstractmethod
    def fetch_prices(self) -> PriceLoader:
        pass


@dataclass
class TestMrMktUseCaseFactory(MrMktUseCaseFactory):
    env: MrMktEnvironment

    def fetch_financials(self):
        return FinancialLoader(self.env.remote, self.env.local)

    def fetch_prices(self) -> PriceLoader:
        return PriceLoader(self.env.remote, self.env.local, self.env.clock)
