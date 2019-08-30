from dataclasses import dataclass
from financial import FinancialGateway
from finrepo import FinancialRepository
from sql import Duplicate


@dataclass
class FinancialLoaderRequest:
    symbol: str


class FinancialLoaderResult:
    def on_load_symbol(self, symbol: str):
        pass


class FinancialLoader(object):
    result: FinancialLoaderResult

    def __init__(self, fin_gate: FinancialGateway, fin_db: FinancialRepository):
        self.fin_db = fin_db
        self.fin_gate = fin_gate

    def run(self, request: FinancialLoaderRequest, result: FinancialLoaderResult):
        self.result = result
        if request.symbol is not None:
            self.load(request.symbol)
        else:
            self.load_all()

    def load(self, symbol: str):
        self.result.on_load_symbol(symbol)
        income_statements = self.fin_gate.income_statement(symbol)
        for i in income_statements:
            try:
                self.fin_db.add_income(i)
            except Duplicate:
                pass

        balance_sheets = self.fin_gate.balance_sheet(symbol)
        for b in balance_sheets:
            try:
                self.fin_db.add_balance_sheet(b)
            except Duplicate:
                pass

    def load_all(self):
        for symbol in self.fin_gate.get_stocks():
            self.load(symbol)
