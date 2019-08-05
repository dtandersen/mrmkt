from balance_sheet import BalanceSheet
from income_statement import IncomeStatement


class FinancialGateway():
    def balance_sheet(self, symbol) -> BalanceSheet:
        pass

    def income_statement(self, symbol) -> IncomeStatement:
        pass

    def closing_price(self, symbol, date) -> IncomeStatement:
        pass


class InMemoryFinancialGateway(FinancialGateway):
    balances = {}
    incomes = {}
    close = {}

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
