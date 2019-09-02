import datetime

from common.finrepo import InMemoryFinancialRepository
from entity.balance_sheet import BalanceSheet
from entity.income_statement import IncomeStatement
from entity.stock_price import StockPrice


class CannedData(InMemoryFinancialRepository):
    def __init__(self):
        super().__init__()
        self.add_apple_financials()
        self.add_google_financials()
        self.add_nvidia_financials()
        self.add_spy_financials()

    def add_google_financials(self):
        self.stocks.append('GOOG')
        self.add_income(IncomeStatement(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            netIncome=30736000000.0,
            waso=750000000
        ))

        self.add_balance_sheet(BalanceSheet(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            totalAssets=232792000000.0,
            totalLiabilities=1264000000.0
        ))

        self.add_price(StockPrice(
            symbol='GOOG',
            date=datetime.date(2014, 6, 13),
            open=552.26,
            high=552.3,
            low=545.56,
            close=551.76,
            volume=1217176.0
        ))

        self.add_price(StockPrice(
            symbol='GOOG',
            date=datetime.date(2014, 6, 16),
            open=549.26,
            high=549.62,
            low=541.52,
            close=544.28,
            volume=1704027.0
        ))

    def add_nvidia_financials(self):
        self.stocks.append('NVDA')
        self.add_income(IncomeStatement(
            symbol='NVDA',
            date=datetime.date(2019, 1, 27),
            netIncome=4141000000.0,
            waso=625000000
        ))

        self.add_balance_sheet(BalanceSheet(
            symbol='NVDA',
            date=datetime.date(2019, 1, 27),
            totalAssets=13292000000.0,
            totalLiabilities=3950000000.0
        ))

    def add_apple_financials(self):
        self.stocks.append('AAPL')
        self.add_income(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            netIncome=59531000000.0,
            waso=5000109000
        ))

        self.add_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        ))

        self.add_income(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            netIncome=48351000000.0,
            waso=5251692000
        ))

        self.add_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        ))

        self.add_price(StockPrice(
            symbol='AAPL',
            date=datetime.date(2014, 6, 13),
            open=84.5035,
            high=84.7235,
            low=83.2937,
            close=83.6603,
            volume=5.452528E7
        ))

    def add_spy_financials(self):
        self.stocks.append('SPY')
