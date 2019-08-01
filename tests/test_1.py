import unittest

from balance_sheet import BalanceSheet
from income_statement import IncomeStatement


class Analysis():
    def __init__(self):
        self.bookValue = None
        self.eps = None
        self.equity = None
        self.pe = None

    pass


class Buffet():
    def analyze(self, inc: IncomeStatement, bal: BalanceSheet) -> Analysis:
        analysis = Analysis()
        analysis.equity = bal.totalAssets - bal.totalLiabilities
        analysis.eps = inc.netIncome / inc.waso
        analysis.bookValue = analysis.equity / inc.waso
        analysis.pe = analysis.bookValue / analysis.eps
        return analysis


class Dbxxx():
    balances = {}
    incomes = {}

    def addBalanceSheet(self, bal : BalanceSheet):
        self.balances[bal.symbol] = bal

    def getBalanceSheet(self, symbol):
        return self.balances[symbol]

    def addIncome(self, param : IncomeStatement):
        self.incomes[param.symbol] = param

    def getIncomeStatement(self, symbol):
        return self.incomes[symbol]


class TestStringMethods(unittest.TestCase):
    def setUp(self):
        self.q = Dbxxx()
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
