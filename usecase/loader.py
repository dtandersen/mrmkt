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

    def __init__(self, fin_gate: ReadOnlyFinancialRepository, fin_db: FinancialRepository):
        self.fin_db = fin_db
        self.fin_gate = fin_gate

    def execute(self, request: FinancialLoaderRequest, result: FinancialLoaderResult):
        self.result = result
        if request.symbol is not None:
            self.load(request.symbol)
        else:
            self.load_all()

    def load(self, symbol: str):
        self.result.on_load_symbol(symbol)
        prices = self.fin_gate.list_prices(symbol)
        for price in prices:
            try:
                self.fin_db.add_price(price)
            except Duplicate:
                pass

        income_statements = self.fin_gate.list_income_statements(symbol)
        for i in income_statements:
            try:
                self.fin_db.add_income(i)
            except Duplicate:
                pass

        balance_sheets = self.fin_gate.list_balance_sheets(symbol)
        for b in balance_sheets:
            try:
                self.fin_db.add_balance_sheet(b)
            except Duplicate:
                pass

    def load_all(self):
        for symbol in self.fin_gate.get_symbols():
            self.load(symbol)
