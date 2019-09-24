from abc import abstractmethod
from dataclasses import dataclass

from common.inmemfinrepo import FinancialRepository
from common.finrepo import ReadOnlyFinancialRepository
from usecase.fetch import FinancialLoader
from usecase.price_loader import PriceLoader


class MrMktUseCaseFactory:
    @abstractmethod
    def fetch_financials(self) -> FinancialLoader:
        pass

    @abstractmethod
    def fetch_prices(self) -> PriceLoader:
        pass


@dataclass
class TestMrMktUseCaseFactory(MrMktUseCaseFactory):
    fingate: ReadOnlyFinancialRepository
    findb: FinancialRepository

    def fetch_financials(self):
        return FinancialLoader(self.fingate, self.findb)

    def fetch_prices(self) -> PriceLoader:
        return PriceLoader(self.fingate, self.findb)