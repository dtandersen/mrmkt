from abc import abstractmethod
from dataclasses import dataclass

from financial import FinancialGateway
from finrepo import FinancialRepository
from loader import FinancialLoader


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
