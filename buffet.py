from balance_sheet import BalanceSheet
from income_statement import IncomeStatement


class Analysis():
    def __init__(self):
        self.bookValue = None
        self.eps = None
        self.equity = None
        self.pe = None

    pass


class Buffet():
    def analyze(self, inc: IncomeStatement, bal: BalanceSheet) -> Analysis:
        analysis = Analysis()
        analysis.equity = bal.totalAssets - bal.totalLiabilities
        analysis.eps = inc.netIncome / inc.waso
        analysis.bookValue = analysis.equity / inc.waso
        analysis.pe = analysis.bookValue / analysis.eps
        return analysis
