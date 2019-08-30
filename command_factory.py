from abc import abstractmethod
from dataclasses import dataclass

from common.financial import FinancialGateway
from common.finrepo import FinancialRepository
from usecase.loader import FinancialLoader


class MrMktCommandFactory:
    @abstractmethod
    def loader(self) -> FinancialLoader:
        pass


@dataclass
class TestMrMktCommandFactory(MrMktCommandFactory):
    fingate: FinancialGateway
    findb: FinancialRepository

    def loader(self):
        return FinancialLoader(self.fingate, self.findb)
