import unittest

from balance_sheet import BalanceSheet
from financial import InMemoryFinancialGateway
from income_statement import IncomeStatement
from findb import InMemoryFinDb
from loader import StockLoader


class TestStringMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.fin_gate = InMemoryFinancialGateway()
        self.db = InMemoryFinDb()
        self.loader = StockLoader(self.fin_gate, self.db)

        self.fin_gate.stocks = ['SPY', 'AAPL', 'NVDA']

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

    def test_get(self):
        self.loader.load_all()
        self.assertEqual(vars(IncomeStatement(
            symbol='AAPL',
            date='2018-09-29',
            netIncome=59531000000.0,
            waso=5000109000.0
        )), vars(self.db.get_income_statement('AAPL')))

        self.assertEqual(vars(BalanceSheet(
            symbol='AAPL',
            date='2018-09-29',
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )), vars(self.db.get_balance_sheet('AAPL')))

        self.assertEqual(vars(IncomeStatement(
            symbol='NVDA',
            date='2019-01-27',
            netIncome=4141000000.0,
            waso=625000000.0
        )), vars(self.db.get_income_statement('NVDA')))

        self.assertEqual(vars(BalanceSheet(
            symbol='NVDA',
            date='2019-01-27',
            totalAssets=13292000000.0,
            totalLiabilities=3950000000.0
        )), vars(self.db.get_balance_sheet('NVDA')))

    def test_load_empty(self):
        self.loader.load_all()
        self.assertEqual(vars(IncomeStatement(
            symbol='AAPL',
            date='2018-09-29',
            netIncome=59531000000.0,
            waso=5000109000.0
        )), vars(self.db.get_income_statement('AAPL')))

        self.assertEqual(vars(BalanceSheet(
            symbol='AAPL',
            date='2018-09-29',
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )), vars(self.db.get_balance_sheet('AAPL')))

        self.assertEqual(vars(IncomeStatement(
            symbol='NVDA',
            date='2019-01-27',
            netIncome=4141000000.0,
            waso=625000000.0
        )), vars(self.db.get_income_statement('NVDA')))

        self.assertEqual(vars(BalanceSheet(
            symbol='NVDA',
            date='2019-01-27',
            totalAssets=13292000000.0,
            totalLiabilities=3950000000.0
        )), vars(self.db.get_balance_sheet('NVDA')))
