import unittest

from balance_sheet import BalanceSheet
from financial import FinancialGateway, InMemoryFinancialGateway
from income_statement import IncomeStatement
from findb import FinancialRepository, InMemoryFinDb


class StockLoader(object):
    def __init__(self, fin_gate: FinancialGateway, fin_db: FinancialRepository):
        self.fin_db = fin_db
        self.fin_gate = fin_gate

    def load_all(self):
        for symbol in self.fin_gate.get_stocks():
            income_statement = self.fin_gate.income_statement(symbol)
            self.fin_db.add_income(income_statement)

            balance_sheet = self.fin_gate.balance_sheet(symbol)
            self.fin_db.add_balance_sheet(balance_sheet)


class TestStringMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.fin_gate = InMemoryFinancialGateway()
        self.db = InMemoryFinDb()
        self.loader = StockLoader(self.fin_gate, self.db)

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
