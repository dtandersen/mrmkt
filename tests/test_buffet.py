import unittest

from balance_sheet import BalanceSheet
from buffet import Buffet
from finrepo import InMemoryFinancialRepository
from income_statement import IncomeStatement


class TestStringMethods(unittest.TestCase):
    def setUp(self):
        self.finrepo = InMemoryFinancialRepository()
        self.finrepo.add_income(IncomeStatement(
            symbol='ICECREAM',
            date='2019-08-04',
            netIncome=20000,
            waso=10000
        ))

        self.finrepo.add_income(IncomeStatement(
            symbol='ICECREAM',
            date='2020-08-04',
            netIncome=30000,
            waso=12500
        ))
        self.finrepo.add_balance_sheet(BalanceSheet(
            symbol='ICECREAM',
            date='2019-08-04',
            totalAssets=44000,
            totalLiabilities=37000
        ))
        self.finrepo.add_balance_sheet(BalanceSheet(
            symbol='ICECREAM',
            date='2020-08-04',
            totalAssets=48000,
            totalLiabilities=36000
        ))
        self.finrepo.add_close_price('ICECREAM', '2019-08-04', 10)
        self.finrepo.add_close_price('ICECREAM', '2020-08-04', 12)

        self.finrepo.add_income(IncomeStatement(
            symbol='PIZZA',
            date='2020-02-20',
            netIncome=15000,
            waso=1000
        ))
        self.finrepo.add_balance_sheet(BalanceSheet(
            symbol='PIZZA',
            date='2020-02-20',
            totalAssets=5000,
            totalLiabilities=12500
        ))
        self.finrepo.add_close_price('PIZZA', '2020-02-20', 5)

        self.buf = Buffet(self.finrepo)

    def test_upper(self):
        res = self.buf.analyze('ICECREAM')

        self.assertEqual(vars(res[0]), {
            "symbol": 'ICECREAM',
            "date": '2019-08-04',
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
            'assets': 48000,
            'bookValue': 0.96,
            'buffetNumber': 62.5,
            'date': '2020-08-04',
            'eps': 2.4,
            'equity': 12000,
            'liabilities': 36000,
            'marginOfSafety': 0.08,
            'netIncome': 30000,
            'pe': 5.0,
            'priceToBookValue': 12.5,
            'sharesOutstanding': 12500,
            'symbol': 'ICECREAM'})

    def test_2(self):
        res = self.buf.analyze('PIZZA')

        self.assertEqual(vars(res[0]), {
            "symbol": 'PIZZA',
            "date": '2020-02-20',
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
