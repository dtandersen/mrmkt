import unittest

from entity.analysis import Analysis
from entity.balance_sheet import BalanceSheet
from entity.cash_flow import CashFlow
from entity.enterprise_value import EnterpriseValue
from models.buffet import BuffetModel
from tests.test_sqlfinrepo import to_date
from usecase.runmodel import RunModel, RunModelRequest
from common.inmemfinrepo import InMemoryFinancialRepository
from entity.income_statement import IncomeStatement


class TestBuffetModel(unittest.TestCase):
    def setUp(self):
        self.finrepo = InMemoryFinancialRepository()

        self.with_income(IncomeStatement(
            symbol='ICECREAM',
            date=to_date('2019-08-04'),
            netIncome=20000,
            waso=10000))
        self.with_balance_sheet(BalanceSheet(
            symbol='ICECREAM',
            date=to_date('2019-08-04'),
            totalAssets=44000,
            totalLiabilities=37000))
        self.with_cash_flow(CashFlow(
            symbol='ICECREAM',
            date=to_date('2019-08-04'),
            operating_cash_flow=1000,
            capital_expenditure=1000,
            free_cash_flow=1000,
            dividend_payments=1000))
        self.with_enterprise_value(EnterpriseValue(
            symbol='ICECREAM',
            date=to_date('2019-08-04'),
            stock_price=10,
            shares_outstanding=10000,
            market_cap=10000))
        self.with_close_price('ICECREAM', '2019-08-05', 10)  # one day after

        self.with_income(IncomeStatement(
            symbol='ICECREAM',
            date=to_date('2020-08-04'),
            netIncome=30000,
            waso=12500))
        self.with_balance_sheet(BalanceSheet(
            symbol='ICECREAM',
            date=to_date('2020-08-04'),
            totalAssets=48000,
            totalLiabilities=36000))
        self.with_cash_flow(CashFlow(
            symbol='ICECREAM',
            date=to_date('2020-08-04'),
            operating_cash_flow=1000,
            capital_expenditure=1000,
            free_cash_flow=1000,
            dividend_payments=1000))
        self.with_enterprise_value(EnterpriseValue(
            symbol='ICECREAM',
            date=to_date('2020-08-04'),
            stock_price=12,
            shares_outstanding=12500,
            market_cap=10000))

        self.with_close_price('ICECREAM', '2020-08-04', 12)

        self.with_income(IncomeStatement(
            symbol='PIZZA',
            date=to_date('2020-02-20'),
            netIncome=15000,
            waso=1000))
        self.with_balance_sheet(BalanceSheet(
            symbol='PIZZA',
            date=to_date('2020-02-20'),
            totalAssets=5000,
            totalLiabilities=12500))
        self.with_cash_flow(CashFlow(
            symbol='PIZZA',
            date=to_date('2020-02-20'),
            operating_cash_flow=1000,
            capital_expenditure=1000,
            free_cash_flow=1000,
            dividend_payments=1000))
        self.with_enterprise_value(EnterpriseValue(
            symbol='PIZZA',
            date=to_date('2020-02-20'),
            stock_price=5,
            shares_outstanding=1000,
            market_cap=10000))

        self.buf = RunModel(self.finrepo)

    def test_analyze_two_periods(self):
        self.when_analyzed('ICECREAM')

        res = self.finrepo.get_analysis('ICECREAM')

        self.assertEqual(vars(res[0]), {
            "symbol": 'ICECREAM',
            "date": to_date('2019-08-04'),
            "equity": 7000,
            "netIncome": 20000,
            "eps": 2,
            "bookValue": .70,
            "pe": 5,
            "priceToBookValue": 14.285714285714286,
            "buffetNumber": 71.42857142857143,
            "marginOfSafety": .07,
            "assets": 44000,
            "liabilities": 37000,
            "sharesOutstanding": 10000
        })

        self.assertEqual(vars(res[1]), {
            'symbol': 'ICECREAM',
            'date': to_date('2020-08-04'),
            'equity': 12000,
            'netIncome': 30000,
            'eps': 2.4,
            'bookValue': 0.96,
            'pe': 5.0,
            'priceToBookValue': 12.5,
            'buffetNumber': 62.5,
            'marginOfSafety': 0.08,
            'assets': 48000,
            'liabilities': 36000,
            'sharesOutstanding': 12500,
            })

    def test_pizza(self):
        self.when_analyzed('PIZZA')

        res = self.finrepo.get_analysis('PIZZA')

        self.assertEqual(vars(res[0]), {
            "symbol": 'PIZZA',
            "date": to_date('2020-02-20'),
            "equity": -7500,
            "netIncome": 15000,
            "eps": 15,
            "bookValue": -7500 / 1000,
            "pe": 0.3333333333333333,
            "priceToBookValue": -0.6666666666666666,
            "buffetNumber": -0.2222222222222222,
            "marginOfSafety": -1.5,
            "assets": 5000,
            "liabilities": 12500,
            "sharesOutstanding": 1000
        })

    def test_overwrite(self):
        self.finrepo.add_analysis(Analysis(
            symbol='PIZZA',
            date=to_date('2020-02-20'),
            equity=-7500,
            netIncome=15000,
            eps=15,
            bookValue=-7500 / 1000,
            pe=0.3333333333333333,
            priceToBookValue=-0.6666666666666666,
            buffetNumber=-0.2222222222222222,
            marginOfSafety=-1.5,
            assets=5000,
            liabilities=12500,
            sharesOutstanding=1000
        ))

        symbol = 'PIZZA'
        self.when_analyzed(symbol)

        analysis = self.finrepo.get_analysis('PIZZA')

        self.assertEqual(vars(analysis[0]), {
            "symbol": 'PIZZA',
            "date": to_date('2020-02-20'),
            "equity": -7500,
            "netIncome": 15000,
            "eps": 15,
            "bookValue": -7500 / 1000,
            "pe": 0.3333333333333333,
            "priceToBookValue": -0.6666666666666666,
            "buffetNumber": -0.2222222222222222,
            "marginOfSafety": -1.5,
            "assets": 5000,
            "liabilities": 12500,
            "sharesOutstanding": 1000
        })

    def when_analyzed(self, symbol):
        self.buf.execute(RunModelRequest(symbol=symbol, model_class=BuffetModel))

    def with_close_price(self, symbol, date, price):
        self.finrepo.add_close_price(symbol, to_date(date), price)

    def with_balance_sheet(self, sheet):
        self.finrepo.add_balance_sheet(sheet)

    def with_income(self, statement):
        self.finrepo.add_income(statement)

    def with_cash_flow(self, sheet):
        self.finrepo.add_cash_flow(sheet)

    def with_enterprise_value(self, sheet):
        self.finrepo.add_enterprise_value(sheet)
