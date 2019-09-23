from abc import abstractmethod
from dataclasses import dataclass

from common.inmemfinrepo import FinancialRepository
from common.finrepo import ReadOnlyFinancialRepository
from usecase.fetch import FinancialLoader


class MrMktUseCaseFactory:
    @abstractmethod
    def fetch_financials(self) -> FinancialLoader:
        pass


@dataclass
class TestMrMktUseCaseFactory(MrMktUseCaseFactory):
    fingate: ReadOnlyFinancialRepository
    findb: FinancialRepository

    def fetch_financials(self):
        return FinancialLoader(self.fingate, self.findb)
