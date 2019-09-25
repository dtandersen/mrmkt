from dataclasses import dataclass

from mrmkt.common.finrepo import ReadOnlyFinancialRepository, FinancialRepository
from mrmkt.common.sql import Duplicate


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
        self.destrepo.add_prices(prices)

        income_statements = self.sourcerepo.list_income_statements(symbol)
        for i in income_statements:
            try:
                self.destrepo.add_income(i)
            except Duplicate:
                pass

        balance_sheets = self.sourcerepo.list_balance_sheets(symbol)
        for c in balance_sheets:
            try:
                self.destrepo.add_balance_sheet(c)
            except Duplicate:
                pass

        cash_flows = self.sourcerepo.list_cash_flows(symbol)
        for c in cash_flows:
            try:
                self.destrepo.add_cash_flow(c)
            except Duplicate:
                pass

        enterprise_value = self.sourcerepo.list_enterprise_value(symbol)
        for e in enterprise_value:
            try:
                self.destrepo.add_enterprise_value(e)
            except Duplicate:
                pass

    def load_all(self):
        for symbol in self.sourcerepo.get_symbols():
            self.load(symbol)
