from balance_sheet import BalanceSheet
from financial import FinancialGateway
from income_statement import IncomeStatement


class Analysis():
    def __init__(self):
        self.netIncome = None
        self.buffetNumber = None
        self.priceToBookValue = None
        self.date = None
        self.symbol = None
        self.sharesOutstanding = None
        self.liabilities = None
        self.assets = None
        self.marginOfSafety = None
        self.bookValue = None
        self.eps = None
        self.equity = None
        self.pe = None

    pass


class Buffet():
    def __init__(self, fin: FinancialGateway):
        self.fin = fin

    def analyze(self, inc: IncomeStatement, bal: BalanceSheet) -> Analysis:
        close = self.fin.closing_price(inc.symbol, inc.date)
        analysis = Analysis()
        analysis.symbol = inc.symbol
        analysis.date = inc.date
        analysis.assets = bal.totalAssets
        analysis.liabilities = bal.totalLiabilities
        analysis.sharesOutstanding = inc.waso
        analysis.netIncome = inc.netIncome
        analysis.equity = bal.totalAssets - bal.totalLiabilities
        analysis.eps = inc.netIncome / inc.waso
        analysis.bookValue = analysis.equity / inc.waso
        analysis.pe = close / analysis.eps
        analysis.priceToBookValue = close / analysis.bookValue
        analysis.buffetNumber = analysis.priceToBookValue * analysis.pe
        market_cap = (close * inc.waso)
        analysis.marginOfSafety = analysis.equity / market_cap
        return analysis
