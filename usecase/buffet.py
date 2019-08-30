from common.finrepo import FinancialRepository
from entity.analysis import Analysis


class Buffet:
    def __init__(self, fin: FinancialRepository):
        self.fin = fin

    def analyze(self, symbol: str) -> None:
        inc2 = self.fin.get_income_statements(symbol)
        bal2 = self.fin.get_balance_sheets(symbol)

        for i in range(len(inc2)):
            inc = inc2[i]
            bal = next((x for x in bal2 if x.date == inc.date), None)
            close = self.fin.get_closing_price(inc.symbol, inc.date)

            analysis = self.anlz(bal, close, inc)
            self.fin.add_analysis(analysis)

    def anlz(self, bal, close, inc) -> Analysis:
        market_cap = (close * inc.waso)
        equity = bal.totalAssets - bal.totalLiabilities
        eps = inc.netIncome / inc.waso
        bookValue = equity / inc.waso
        priceToBookValue = close / bookValue
        pe = close / eps
        analysis = Analysis(
            symbol=inc.symbol,
            date=inc.date,
            assets=bal.totalAssets,
            liabilities=bal.totalLiabilities,
            sharesOutstanding=inc.waso,
            netIncome=inc.netIncome,
            equity=equity,
            eps=inc.netIncome / inc.waso,
            bookValue=bookValue,
            pe=close / eps,
            priceToBookValue=close / bookValue,
            buffetNumber=priceToBookValue * pe,
            marginOfSafety=equity / market_cap
        )

        return analysis
