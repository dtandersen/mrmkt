from abc import abstractmethod
from dataclasses import dataclass

from common.fingate import FinancialGateway
from common.finrepo import FinancialRepository
from usecase.loader import FinancialLoader


class MrMktUseCaseFactory:
    @abstractmethod
    def fetch_financials(self) -> FinancialLoader:
        pass


@dataclass
class TestMrMktUseCaseFactory(MrMktUseCaseFactory):
    fingate: FinancialGateway
    findb: FinancialRepository

    def fetch_financials(self):
        return FinancialLoader(self.fingate, self.findb)