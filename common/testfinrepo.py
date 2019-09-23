import datetime

from common.inmemfinrepo import InMemoryFinancialRepository
from common.util import to_date
from entity.balance_sheet import BalanceSheet
from entity.cash_flow import CashFlow
from entity.enterprise_value import EnterpriseValue
from entity.income_statement import IncomeStatement
from entity.stock_price import StockPrice


class FinancialTestRepository(InMemoryFinancialRepository):
    def with_all(self):
        self.add_apple_financials()
        self.add_google_financials()
        self.add_nvidia_financials()
        self.add_spy_financials()
        self.add_walmart()
        self.with_disney()
        return self

    def add_google_financials(self):
        self.stocks.add('GOOG')
        self.add_income(IncomeStatement(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            netIncome=30736000000.0,
            waso=750000000,
            consolidated_net_income=-1
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
        self.stocks.add('NVDA')
        self.add_income(IncomeStatement(
            symbol='NVDA',
            date=datetime.date(2019, 1, 27),
            netIncome=4141000000.0,
            waso=625000000,
            consolidated_net_income=-1
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
        self.stocks.add('AAPL')
        self.add_income(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            netIncome=59531000000.0,
            waso=5000109000,
            consolidated_net_income=-1
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
            waso=5251692000,
            consolidated_net_income=-1
        ))

        self.add_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        ))

        self.add_cash_flow(CashFlow(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            operating_cash_flow=77434000000.0,
            capital_expenditure=-13313000000.0,
            free_cash_flow=64121000000.0,
            dividend_payments=-13712000000.0,
        ))

        self.add_enterprise_value(EnterpriseValue(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            stock_price=224.6375,
            shares_outstanding=5000109000.0,
            market_cap=1.1232119854875E12
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

        return self

    def add_netflix_financials(self):
        self.stocks.add('NFLX')
        self.add_income(IncomeStatement(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            netIncome=1211242000.0,
            waso=451244000,
            consolidated_net_income=-1
        ))
        self.add_balance_sheet(BalanceSheet(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            totalAssets=25974400000.0,
            totalLiabilities=20735635000.0
        ))
        self.add_cash_flow(CashFlow(
            symbol='NFLX',
            date=to_date('2018-12-31'),
            operating_cash_flow=-2680479000.0,
            capital_expenditure=-212532000.0,
            free_cash_flow=-2893011000.0,
            dividend_payments=0

        ))
        self.add_enterprise_value(EnterpriseValue(
            symbol='NFLX',
            date=to_date('2018-12-31'),
            stock_price=267.66,
            shares_outstanding=451244000.0,
            market_cap=1.2077996904000002E11

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
        self.stocks.add('SPY')

    def addSpyFinancials(self):
        self.stocks.add('SPY')

    def add_walmart(self):
        self.stocks.add('WMT')

        self.add_income(IncomeStatement(
            symbol='WMT',
            date=to_date('2017-01-31'),
            netIncome=13643000000.0,
            waso=3112000000,
            consolidated_net_income=14293000000.0
        ))
        self.add_balance_sheet(BalanceSheet(
            symbol='WMT',
            date=to_date('2017-01-31'),
            totalAssets=198825000000.0,
            totalLiabilities=10265000000.0,
            non_current_assets=51362000000.0,
            inventories=43046000000.0,
            receivables=5835000000.0
        ))
        self.add_cash_flow(CashFlow(
            symbol='WMT',
            date=to_date('2017-01-31'),
            operating_cash_flow=-31673000000.0,
            capital_expenditure=-10163000000.0,
            free_cash_flow=21510000000.0,
            dividend_payments=-6216000000.0

        ))
        self.add_enterprise_value(EnterpriseValue(
            symbol='WMT',
            date=to_date('2017-01-31'),
            stock_price=62.5478,
            shares_outstanding=3112000000.0,
            market_cap=1.946487536E11

        ))

    def with_disney(self):
        self.stocks.add('DIS')

        self.add_income(IncomeStatement(
            symbol='DIS',
            date=to_date('2018-09-29'),
            netIncome=12598000000.0,
            waso=1507000000,
            consolidated_net_income=13066000000.0
        ))
        self.add_balance_sheet(BalanceSheet(
            symbol='DIS',
            date=to_date('2018-09-29'),
            totalAssets=98598000000.0,
            totalLiabilities=45766000000.0,
            non_current_assets=27906000000.0,
            inventories=1392000000.0,
            receivables=9334000000.0
        ))
        self.add_cash_flow(CashFlow(
            symbol='DIS',
            date=to_date('2018-09-29'),
            operating_cash_flow=14295000000.0,
            capital_expenditure=-4465000000.0,
            free_cash_flow=9830000000.0,
            dividend_payments=-2515000000.0,
            deprec=3011000000.0,
        ))
        self.add_enterprise_value(EnterpriseValue(
            symbol='DIS',
            date=to_date('2018-09-29'),
            stock_price=115.3453,
            shares_outstanding=1507000000,
            market_cap=1.738253671E11

        ))

        return self

    def with_spy(self):
        self.stocks.add('SPY')
        self.add_price(StockPrice(
            symbol="SPY",
            date=to_date("2019-09-16"),
            open=299.85,
            high=300.5,
            low=299.78,
            close=300.195,
            volume=4.6779547E7
        ))
        self.add_price(StockPrice(
            symbol="SPY",
            date=to_date("2019-09-17"),
            open=299.84,
            high=300.965,
            low=299.84,
            close=300.965,
            volume=4.6916222E7
        ))
        self.add_price(StockPrice(
            symbol="SPY",
            date=to_date("2019-09-18"),
            open=300.83,
            high=301.015,
            low=298.79,
            close=301.015,
            volume=4.6963889E7
        ))
        self.add_price(StockPrice(
            symbol="SPY",
            date=to_date("2019-09-19"),
            open=301.49,
            high=302.34,
            low=301.015,
            close=301.015,
            volume=4.695743E7
        ))
        self.add_price(StockPrice(
            symbol="SPY",
            date=to_date("2019-09-20"),
            open=300.31,
            high=300.47,
            low=298.45,
            close=298.67,
            volume=4.6894282E7
        ))

        return self
