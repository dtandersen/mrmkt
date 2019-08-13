from typing import List

from balance_sheet import BalanceSheet
from income_statement import IncomeStatement


class FinancialGateway():
    def balance_sheet(self, symbol) -> BalanceSheet:
        pass

    def income_statement(self, symbol) -> IncomeStatement:
        pass

    def closing_price(self, symbol, date) -> IncomeStatement:
        pass

    def get_stocks(self) -> List[str]:
        pass


class InMemoryFinancialGateway(FinancialGateway):
    def __init__(self):
        self.balances = dict()
        self.incomes = dict()
        self.close = dict()

    def addBalanceSheet(self, bal : BalanceSheet):
        self.balances[bal.symbol] = bal

    def balance_sheet(self, symbol) -> BalanceSheet:
        return self.balances[symbol]

    def closing_price(self, symbol, date) -> IncomeStatement:
        return self.close[f'{symbol}-{date}']

    def addIncome(self, param : IncomeStatement):
        self.incomes[param.symbol] = param

    def income_statement(self, symbol) -> IncomeStatement:
        return self.incomes[symbol]

    def add_close_price(self, symbol, date, close_price):
        self.close[f'{symbol}-{date}'] = close_price

    def get_stocks(self) -> List[str]:
        stocks = [income_statement.symbol for income_statement in self.incomes.values()]
        return stocks
