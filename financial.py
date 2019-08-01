from balance_sheet import BalanceSheet
from income_statement import IncomeStatement


class FinancialGateway():
    def getBalanceSheet(self, symbol) -> BalanceSheet:
        pass

    def getIncomeStatement(self, symbol) -> IncomeStatement:
        pass


class InMemoryFinancialGateway(FinancialGateway):
    balances = {}
    incomes = {}

    def addBalanceSheet(self, bal : BalanceSheet):
        self.balances[bal.symbol] = bal

    def getBalanceSheet(self, symbol) -> BalanceSheet:
        return self.balances[symbol]

    def addIncome(self, param : IncomeStatement):
        self.incomes[param.symbol] = param

    def getIncomeStatement(self, symbol) -> IncomeStatement:
        return self.incomes[symbol]
