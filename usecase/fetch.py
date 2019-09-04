from dataclasses import dataclass

from common.inmemfinrepo import FinancialRepository
from common.onion import ReadOnlyFinancialRepository
from common.sql import Duplicate


@dataclass
class FinancialLoaderRequest:
    symbol: str


class FinancialLoaderResult:
    def on_load_symbol(self, symbol: str):
        pass


class UseCase:
    result: object


class FinancialLoader(UseCase):
    result: FinancialLoaderResult

    def __init__(self, sourcerepo: ReadOnlyFinancialRepository, destrepo: FinancialRepository):
        self.destrepo = destrepo
        self.sourcerepo = sourcerepo

    def execute(self, request: FinancialLoaderRequest, result: FinancialLoaderResult):
        self.result = result
        if request.symbol is not None:
            self.load(request.symbol)
        else:
            self.load_all()

    def load(self, symbol: str):
        self.result.on_load_symbol(symbol)
        prices = self.sourcerepo.list_prices(symbol)
        for price in prices:
            try:
                self.destrepo.add_price(price)
            except Duplicate:
                pass

        income_statements = self.sourcerepo.list_income_statements(symbol)
        for i in income_statements:
            try:
                self.destrepo.add_income(i)
            except Duplicate:
                pass

        balance_sheets = self.sourcerepo.list_balance_sheets(symbol)
        for b in balance_sheets:
            try:
                self.destrepo.add_balance_sheet(b)
            except Duplicate:
                pass

    def load_all(self):
        for symbol in self.sourcerepo.get_symbols():
            self.load(symbol)
