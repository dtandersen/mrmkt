import datetime

from common.inmemfinrepo import InMemoryFinancialRepository
from common.util import to_date
from entity.balance_sheet import BalanceSheet
from entity.income_statement import IncomeStatement
from entity.stock_price import StockPrice


class FinancialTestRepository(InMemoryFinancialRepository):
    def with_all(self):
        self.add_apple_financials()
        self.add_google_financials()
        self.add_nvidia_financials()
        self.add_spy_financials()
        return self

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
        self.add_price(StockPrice(
            symbol='GOOG',
            date=datetime.date(2018, 11, 30),
            open=1089.07,
            high=1095.57,
            low=1077.88,
            close=1094.43,
            volume=2580612.0
        ))
        self.add_price(StockPrice(
            symbol='GOOG',
            date=datetime.date(2018, 12, 3),
            open=1103.12,
            high=1104.42,
            low=1049.98,
            close=1050.82,
            volume=2345166.0
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

        self.add_price(StockPrice(
            symbol='NVDA',
            date=datetime.date(2014, 6, 13),
            open=18.8814,
            high=18.891,
            low=18.5272,
            close=18.7091,
            volume=5696281.0
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

    def add_netflix_financials(self):
        self.stocks.append('NFLX')
        self.add_income(IncomeStatement(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            netIncome=1211242000.0,
            waso=451244000
        ))

        self.add_balance_sheet(BalanceSheet(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            totalAssets=25974400000.0,
            totalLiabilities=20735635000.0
        ))
        self.add_price(StockPrice(
            symbol='NFLX',
            date=to_date('2018-12-31'),
            open=260.16,
            high=270.1001,
            low=260.0,
            close=267.66,
            volume=1.350892E7
        ))
        self.add_price(StockPrice(
            symbol='NFLX',
            date=to_date('2019-01-02'),
            open=259.28,
            high=269.7499,
            low=256.58,
            close=267.66,
            volume=1.1679528E7
        ))

    def add_spy_financials(self):
        self.stocks.append('SPY')


    def addSpyFinancials(self):
        self.stocks.append('SPY')
