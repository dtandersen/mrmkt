import unittest

from balance_sheet import BalanceSheet
from buffet import Buffet
from financial import InMemoryFinancialGateway
from income_statement import IncomeStatement

class TestStringMethods(unittest.TestCase):
    def setUp(self):
        self.q = InMemoryFinancialGateway()
        self.q.addIncome(IncomeStatement(
            symbol='ICECREAM',
            netIncome=20000,
            waso=10000
        ))
        self.q.addBalanceSheet(BalanceSheet(
            symbol='ICECREAM',
            totalAssets=40000,
            totalLiabilities=33000
        ))

        self.q.addIncome(IncomeStatement(
            symbol='PIZZA',
            netIncome=15000,
            waso=1000
        ))
        self.q.addBalanceSheet(BalanceSheet(
            symbol='PIZZA',
            totalAssets=5000,
            totalLiabilities=12500
        ))

    def test_upper(self):
        inc = self.q.getIncomeStatement('ICECREAM')
        bal = self.q.getBalanceSheet('ICECREAM')
        buf = Buffet()
        res = buf.analyze(inc, bal)
        self.assertEqual(7000, res.equity)
        self.assertEqual(2, res.eps)
        self.assertEqual(7000 / 10000, res.bookValue)
        self.assertEqual(.7 / 2, res.pe)

    def test_2(self):
        inc = self.q.getIncomeStatement('PIZZA')
        bal = self.q.getBalanceSheet('PIZZA')
        buf = Buffet()
        res = buf.analyze(inc, bal)
        self.assertEqual(-7500, res.equity)
        self.assertEqual(15, res.eps)
        self.assertEqual(-7500 / 1000, res.bookValue)
        self.assertEqual(-7.5 / 15, res.pe)
