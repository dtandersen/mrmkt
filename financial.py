from typing import List, Optional

from balance_sheet import BalanceSheet
from income_statement import IncomeStatement


class FinancialGateway():
    def balance_sheet(self, symbol) -> List[BalanceSheet]:
        pass

    def income_statement(self, symbol) -> List[IncomeStatement]:
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

    def addBalanceSheet(self, balance_sheet: BalanceSheet):
        self.balances[f"{balance_sheet.symbol}-{balance_sheet.date}"] = balance_sheet

    def balance_sheet(self, symbol: str) -> List[BalanceSheet]:
        return list(filter(lambda b: b.symbol == symbol, self.balances.values()))

    def closing_price(self, symbol, date) -> Optional[float]:
        return self.close[f'{symbol}-{date}']

    def addIncome(self, income_statement : IncomeStatement):
        self.incomes[f"{income_statement.symbol}-{income_statement.date}"] = income_statement

    def income_statement(self, symbol: str) -> List[IncomeStatement]:
        return list(filter(lambda i: i.symbol == symbol, self.incomes.values()))

    def add_close_price(self, symbol, date, close_price):
        self.close[f'{symbol}-{date}'] = close_price

    def get_stocks(self) -> Optional[List[str]]:
        return self.stocks
