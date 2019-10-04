from abc import abstractmethod
from dataclasses import dataclass

from mrmkt.repo.all import AllRepository, ReadOnlyAllRepository
from mrmkt.usecase.fetch import FinancialLoader
from mrmkt.usecase.price_loader import PriceLoader


class MrMktUseCaseFactory:
    @abstractmethod
    def fetch_financials(self) -> FinancialLoader:
        pass

    @abstractmethod
    def fetch_prices(self) -> PriceLoader:
        pass


@dataclass
class TestMrMktUseCaseFactory(MrMktUseCaseFactory):
    fingate: ReadOnlyAllRepository
    findb: AllRepository

    def fetch_financials(self):
        return FinancialLoader(self.fingate, self.findb)

    def fetch_prices(self) -> PriceLoader:
        return PriceLoader(self.fingate, self.findb)