import unittest

from hamcrest import *

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.common.testfinrepo import FinancialTestRepository
from mrmkt.common.util import to_date
from mrmkt.entity.analysis import Analysis
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.models.buffet import BuffetModel
from mrmkt.repo.provider import MarketDataProvider, ReadOnlyMarketDataProvider
from mrmkt.usecase.runmodel import RunModel, RunModelRequest


class TestBuffetModel(unittest.TestCase):
    def setUp(self):
        self.source = FinancialTestRepository().with_all()
        self.finrepo = InMemoryFinancialRepository()

        self.src = ReadOnlyMarketDataProvider(financials=self.source, prices=self.source, tickers=self.source)
        self.dst = MarketDataProvider(financials=self.finrepo, prices=self.finrepo, tickers=self.finrepo)

        self.with_income(IncomeStatement(
            symbol='ICECREAM',
            date=to_date('2019-08-04'),
            netIncome=20000,
            waso=10000,
            consolidated_net_income=-1
        ))
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
            waso=12500,
            consolidated_net_income=-1
        ))
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
            waso=1000,
            consolidated_net_income=-1
        ))
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

        self.buf = RunModel(self.dst)

    def test_analyze_two_periods(self):
        self.when_analyzed('ICECREAM')

        res = self.finrepo.get_analysis('ICECREAM')

        self.assertEqual(vars(res[0]), {
            "symbol": 'ICECREAM',
            "date": to_date('2019-08-04'),
            "equity": 7000,
            "netIncome": 20000,
            "eps": 2.0,
            "bookValue": .70,
            "pe": 5.0,
            "priceToBookValue": 14.285714285714286,
            "buffetNumber": 71.42857142857143,
            "marginOfSafety": .07,
            "assets": 44000,
            "liabilities": 37000,
            "sharesOutstanding": 10000,
            'current_assets': -2,
            'deprec': 0,
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
            'current_assets': -2,
            'deprec': 0,
        })

    def test_pizza(self):
        self.when_analyzed('PIZZA')

        res = self.finrepo.get_analysis('PIZZA')

        self.assertEqual(vars(res[0]), {
            "symbol": 'PIZZA',
            "date": to_date('2020-02-20'),
            "equity": -7500,
            "netIncome": 15000,
            "eps": 15.0,
            "bookValue": -7500 / 1000,
            "pe": 0.3333333333333333,
            "priceToBookValue": -0.6666666666666666,
            "buffetNumber": -0.2222222222222222,
            "marginOfSafety": -1.5,
            "assets": 5000,
            "liabilities": 12500,
            "sharesOutstanding": 1000,
            'current_assets': -2,
            'deprec': 0
        })

    ### https://www.youtube.com/watch?v=Udh6dhAUsUw ###
    def test_disney_owners_earnings(self):
        self.finrepo.add_income(self.source.get_income_statement('DIS', to_date('2018-09-29')))
        self.finrepo.add_balance_sheet(self.source.get_balance_sheet('DIS', to_date('2018-09-29')))
        self.finrepo.add_cash_flow(self.source.get_cash_flow('DIS', to_date('2018-09-29')))
        self.finrepo.add_enterprise_value(self.source.get_enterprise_value('DIS', to_date('2018-09-29')))

        self.when_analyzed('DIS')

        res = self.finrepo.get_analysis('DIS')

        assert_that(res[0], has_property("netIncome", 12598000000))
        assert_that(res[0], has_property("deprec", 3011000000))
        # changing in working captial: $837m
        # assert_that(res[0], equal_to(Analysis(**{})))

        # assert_that(vars(res[0]), equal_to({
        #     'symbol': 'DIS',
        #     'date': to_date('2018-09-29'),
        #     'assets': 198825000000.0,
        #     'current_assets': 619,
        #     'bookValue': 60.59125964010283,
        #     'buffetNumber': 14.728001021484516,
        #     'eps': 4.3839974293059125,
        #     'equity': 188560000000.0,
        #     'liabilities': 10265000000.0,
        #     'marginOfSafety': 0.9687192777380312,
        #     'netIncome': 12598000000.1,
        #     'pe': 14.267298512057467,
        #     'priceToBookValue': 1.0322908018667798,
        #     'sharesOutstanding': 3112000000.0,
        # }))

    # def test_walmart_owners_earnings(self):
    #     self.finrepo.add_income(self.source.get_income_statement('WMT', to_date('2017-01-31')))
    #     self.finrepo.add_balance_sheet(self.source.get_balance_sheet('WMT', to_date('2017-01-31')))
    #     self.finrepo.add_cash_flow(self.source.get_cash_flow('WMT', to_date('2017-01-31')))
    #     self.finrepo.add_enterprise_value(self.source.get_enterprise_value('WMT', to_date('2017-01-31')))
    #
    #     self.when_analyzed('WMT')
    #
    #     res = self.finrepo.get_analysis('WMT')
    #
    #     self.assertEqual(vars(res[0]), {
    #         'symbol': 'WMT',
    #         'date': to_date('2017-01-31'),
    #         'assets': 198825000000.0,
    #         'current_assets': 619,
    #         'bookValue': 60.59125964010283,
    #         'buffetNumber': 14.728001021484516,
    #         'eps': 4.3839974293059125,
    #         'equity': 188560000000.0,
    #         'liabilities': 10265000000.0,
    #         'marginOfSafety': 0.9687192777380312,
    #         'netIncome': 13643000000.0,
    #         'pe': 14.267298512057467,
    #         'priceToBookValue': 1.0322908018667798,
    #         'sharesOutstanding': 3112000000.0,
    #     })

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
            "sharesOutstanding": 1000,
            'current_assets': -2,
            'deprec': 0,
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
