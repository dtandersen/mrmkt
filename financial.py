from typing import List, Optional

from balance_sheet import BalanceSheet
from income_statement import IncomeStatement


class FinancialGateway():
    def balance_sheet(self, symbol) -> Optional[BalanceSheet]:
        pass

    def income_statement(self, symbol) -> Optional[IncomeStatement]:
        pass

    def closing_price(self, symbol, date) -> Optional[IncomeStatement]:
        pass

    def get_stocks(self) -> Optional[List[str]]:
        pass


class InMemoryFinancialGateway(FinancialGateway):
    def __init__(self):
        self.balances = dict()
        self.incomes = dict()
        self.close = dict()
        self.stocks = []

    def addBalanceSheet(self, bal: BalanceSheet):
        self.balances[bal.symbol] = bal

    def balance_sheet(self, symbol: str) -> Optional[BalanceSheet]:
        if symbol not in self.balances:
            return None

        return self.balances[symbol]

    def closing_price(self, symbol, date) -> Optional[float]:
        return self.close[f'{symbol}-{date}']

    def addIncome(self, param : IncomeStatement):
        self.incomes[param.symbol] = param

    def income_statement(self, symbol: str) -> Optional[IncomeStatement]:
        if symbol not in self.incomes:
            return None

        return self.incomes[symbol]

    def add_close_price(self, symbol, date, close_price):
        self.close[f'{symbol}-{date}'] = close_price

    def get_stocks(self) -> Optional[List[str]]:
        # stocks = [income_statement.symbol for income_statement in self.incomes.values()]
        return self.stocks
