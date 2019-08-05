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
            date='2019-08-04',
            netIncome=20000,
            waso=10000
        ))
        self.q.addBalanceSheet(BalanceSheet(
            symbol='ICECREAM',
            date='2019-08-04',
            totalAssets=44000,
            totalLiabilities=37000
        ))
        self.q.add_close_price('ICECREAM', '2019-08-04', 10)

        self.q.addIncome(IncomeStatement(
            symbol='PIZZA',
            date='2020-02-20',
            netIncome=15000,
            waso=1000
        ))
        self.q.addBalanceSheet(BalanceSheet(
            symbol='PIZZA',
            date='2020-02-20',
            totalAssets=5000,
            totalLiabilities=12500
        ))
        self.q.add_close_price('PIZZA', '2020-02-20', 5)

    def test_upper(self):
        inc = self.q.income_statement('ICECREAM')
        bal = self.q.balance_sheet('ICECREAM')
        buf = Buffet(self.q)
        res = buf.analyze(inc, bal)
        self.assertEqual('ICECREAM', res.symbol)
        self.assertEqual('2019-08-04', res.date)
        self.assertEqual(7000, res.equity)
        self.assertEqual(20000, res.netIncome)
        self.assertEqual(2, res.eps)
        self.assertEqual(.70, res.bookValue)
        self.assertEqual(5, res.pe)
        self.assertEqual(14.285714285714286, res.priceToBookValue)
        self.assertEqual(71.42857142857143, res.buffetNumber)
        self.assertEqual(.07, res.marginOfSafety)
        self.assertEqual(44000, res.assets)
        self.assertEqual(37000, res.liabilities)
        self.assertEqual(10000, res.sharesOutstanding)

    def test_2(self):
        inc = self.q.income_statement('PIZZA')
        bal = self.q.balance_sheet('PIZZA')
        buf = Buffet(self.q)
        res = buf.analyze(inc, bal)
        self.assertEqual('PIZZA', res.symbol)
        self.assertEqual('2020-02-20', res.date)
        self.assertEqual(-7500, res.equity)
        self.assertEqual(15000, res.netIncome)
        self.assertEqual(15, res.eps)
        self.assertEqual(-7500 / 1000, res.bookValue)
        self.assertEqual(0.3333333333333333, res.pe)
        self.assertEqual(-1.5, res.marginOfSafety)
        self.assertEqual(5000, res.assets)
        self.assertEqual(12500, res.liabilities)
        self.assertEqual(1000, res.sharesOutstanding)
