from finrepo import FinancialRepository


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


class Buffet:
    def __init__(self, fin: FinancialRepository):
        self.fin = fin

    def analyze(self, symbol: str) -> Analysis:
        inc2 = self.fin.get_income_statements(symbol)
        bal2 = self.fin.get_balance_sheets(symbol)

        res = []
        for i in range(len(inc2)):
            inc = inc2[i]
            bal = next((x for x in bal2 if x.date == inc.date), None)
            close = self.fin.get_closing_price(inc.symbol, inc.date)

            analysis = self.anlz(bal, close, inc)
            res.append(analysis)

        return res

    def anlz(self, bal, close, inc):
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
