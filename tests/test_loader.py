import unittest

from balance_sheet import BalanceSheet
from financial import InMemoryFinancialGateway
from income_statement import IncomeStatement
from finrepo import InMemoryFinancialRepository
from loader import FinancialLoader


class TestStringMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.fin_gate = InMemoryFinancialGateway()
        self.db = InMemoryFinancialRepository()
        self.loader = FinancialLoader(self.fin_gate, self.db)

    def test_load_multiple_symbols(self):
        self.addGoogleFinancials()
        self.addNvidiaFinancials()

        self.loader.load_all()

        self.assertEqual(vars(IncomeStatement(
            symbol='GOOG',
            date='2018-12',
            netIncome=30736000000.0,
            waso=750000000.0
        )), vars(self.db.get_income_statement('GOOG', '2018-12')))

        self.assertEqual(vars(BalanceSheet(
            symbol='GOOG',
            date='2018-12',
            totalAssets=232792000000.0,
            totalLiabilities=1264000000.0
        )), vars(self.db.get_balance_sheet('GOOG', '2018-12')))

        self.assertEqual(vars(IncomeStatement(
            symbol='NVDA',
            date='2019-01-27',
            netIncome=4141000000.0,
            waso=625000000.0
        )), vars(self.db.get_income_statement('NVDA', '2019-01-27')))

        self.assertEqual(vars(BalanceSheet(
            symbol='NVDA',
            date='2019-01-27',
            totalAssets=13292000000.0,
            totalLiabilities=3950000000.0
        )), vars(self.db.get_balance_sheet('NVDA', '2019-01-27')))

    def test_load_multiple_annual_statements(self):
        self.addAppleFinancials()

        self.loader.load_all()

        self.assertEqual(vars(IncomeStatement(
            symbol='AAPL',
            date='2018-09-29',
            netIncome=59531000000.0,
            waso=5000109000.0
        )), vars(self.db.get_income_statement('AAPL', '2018-09-29')))

        self.assertEqual(vars(IncomeStatement(
            symbol='AAPL',
            date='2017-09-30',
            netIncome=48351000000.0,
            waso=5251692000.0
        )), vars(self.db.get_income_statement('AAPL', '2017-09-30')))

        self.assertEqual(vars(BalanceSheet(
            symbol='AAPL',
            date='2018-09-29',
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )), vars(self.db.get_balance_sheet('AAPL', '2018-09-29')))

        self.assertEqual(vars(BalanceSheet(
            symbol='AAPL',
            date='2017-09-30',
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        )), vars(self.db.get_balance_sheet('AAPL', '2017-09-30')))

    def test_dont_collide_with_existing(self):
        self.addAppleFinancials()

        self.db.add_income(IncomeStatement(
            symbol='AAPL',
            date='2018-09-29',
            netIncome=59531000000.0,
            waso=5000109000.0
        ))

        self.db.add_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date='2018-09-29',
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        ))

        self.loader.load_all()

        self.assertEqual(vars(IncomeStatement(
            symbol='AAPL',
            date='2018-09-29',
            netIncome=59531000000.0,
            waso=5000109000.0
        )), vars(self.db.get_income_statement('AAPL', '2018-09-29')))

        self.assertEqual(vars(BalanceSheet(
            symbol='AAPL',
            date='2018-09-29',
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )), vars(self.db.get_balance_sheet('AAPL', '2018-09-29')))

    def test_spy_has_no_financials(self):
        self.addSpyFinancials()

        self.loader.load_all()

        self.assertEqual(self.db.income_statements, {})
        self.assertEqual(self.db.balance_sheets, {})

    def test_load_goog(self):
        self.addGoogleFinancials()

        self.loader.load('GOOG')

        self.assertEqual(vars(IncomeStatement(
            symbol='GOOG',
            date='2018-12',
            netIncome=30736000000.0,
            waso=750000000.0
        )), vars(self.db.get_income_statement('GOOG', '2018-12')))

        self.assertEqual(vars(BalanceSheet(
            symbol='GOOG',
            date='2018-12',
            totalAssets=232792000000.0,
            totalLiabilities=1264000000.0
        )), vars(self.db.get_balance_sheet('GOOG', '2018-12')))

    def addGoogleFinancials(self):
        self.fin_gate.stocks.append('GOOG')
        self.fin_gate.addIncome(IncomeStatement(
            symbol='GOOG',
            date='2018-12',
            netIncome=30736000000.0,
            waso=750000000.0
        ))

        self.fin_gate.addBalanceSheet(BalanceSheet(
            symbol='GOOG',
            date='2018-12',
            totalAssets=232792000000.0,
            totalLiabilities=1264000000.0
        ))

    def addNvidiaFinancials(self):
        self.fin_gate.stocks.append('NVDA')
        self.fin_gate.addIncome(IncomeStatement(
            symbol='NVDA',
            date='2019-01-27',
            netIncome=4141000000.0,
            waso=625000000.0
        ))

        self.fin_gate.addBalanceSheet(BalanceSheet(
            symbol='NVDA',
            date='2019-01-27',
            totalAssets=13292000000.0,
            totalLiabilities=3950000000.0
        ))

    def addAppleFinancials(self):
        self.fin_gate.stocks.append('AAPL')
        self.fin_gate.addIncome(IncomeStatement(
            symbol='AAPL',
            date='2018-09-29',
            netIncome=59531000000.0,
            waso=5000109000.0
        ))

        self.fin_gate.addBalanceSheet(BalanceSheet(
            symbol='AAPL',
            date='2018-09-29',
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        ))

        self.fin_gate.addIncome(IncomeStatement(
            symbol='AAPL',
            date='2017-09-30',
            netIncome=48351000000.0,
            waso=5251692000.0
        ))

        self.fin_gate.addBalanceSheet(BalanceSheet(
            symbol='AAPL',
            date='2017-09-30',
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        ))

    def addSpyFinancials(self):
        self.fin_gate.stocks.append('SPY')
