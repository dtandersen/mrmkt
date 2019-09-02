import datetime
import unittest
from typing import List

from entity.balance_sheet import BalanceSheet
from common.fingate import TestFinancialGateway
from entity.income_statement import IncomeStatement
from common.finrepo import InMemoryFinancialRepository
from entity.stock_price import StockPrice
from tests.test_sqlfinrepo import to_date
from usecase.loader import FinancialLoader, FinancialLoaderRequest, FinancialLoaderResult
from hamcrest import *


class TestFetch(unittest.TestCase):
    symbols: List[str]

    def setUp(self) -> None:
        self.fin_gate = TestFinancialGateway()
        self.db = InMemoryFinancialRepository()
        self.loader = FinancialLoader(self.fin_gate, self.db)
        self.symbols = []

    def test_load_two_symbols(self):
        self.givenNetflixFinancials()
        self.givenNvidiaFinancials()

        self.whenTheSymbolIsFetched()

        self.assertEqual(self.symbols, ['NFLX', 'NVDA'])

        assert_that(self.incomeStatementFor('NFLX', '2018-12-31'), equal_to(IncomeStatement(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            netIncome=1211242000.0,
            waso=451244000)))

        assert_that(self.db.get_balance_sheet('NFLX', '2018-12-31'), equal_to(BalanceSheet(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            totalAssets=25974400000.0,
            totalLiabilities=20735635000.0)))

        assert_that(self.incomeStatementFor('NVDA', '2019-01-27'), equal_to(IncomeStatement(
            symbol='NVDA',
            date=datetime.date(2019, 1, 27),
            netIncome=4141000000.0,
            waso=625000000
        )))

        assert_that(self.db.get_balance_sheet('NVDA', '2019-01-27'), equal_to(BalanceSheet(
            symbol='NVDA',
            date=datetime.date(2019, 1, 27),
            totalAssets=13292000000.0,
            totalLiabilities=3950000000.0
        )))
        assert_that(self.price_of('NVDA', to_date('2014-06-13')), equal_to(StockPrice(
            symbol='NVDA',
            date=datetime.date(2014, 6, 13),
            open=18.8814,
            high=18.891,
            low=18.5272,
            close=18.7091,
            volume=5696281.0
        )))


    def test_google_bad_dates(self):
        self.givenGoogleFinancials()
        # self.add_google_prices()

        self.whenTheSymbolIsFetched()

        self.assertEqual(self.symbols, ['GOOG'])

        assert_that(self.incomeStatementFor('GOOG', '2018-12-01'), equal_to(IncomeStatement(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            netIncome=30736000000.0,
            waso=750000000)))

        assert_that(self.db.get_balance_sheet('GOOG', '2018-12-01'), equal_to(BalanceSheet(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            totalAssets=232792000000.0,
            totalLiabilities=1264000000.0)))

        assert_that(self.price_of('GOOG', to_date('2018-11-30')), equal_to(StockPrice(
            symbol='GOOG',
            date=datetime.date(2018, 11, 30),
            open=1089.07,
            high=1095.57,
            low=1077.88,
            close=1094.43,
            volume=2580612.0
        )))
        assert_that(self.price_of('GOOG', to_date('2018-12-03')), equal_to(StockPrice(
            symbol='GOOG',
            date=datetime.date(2018, 12, 3),
            open=1103.12,
            high=1104.42,
            low=1049.98,
            close=1050.82,
            volume=2345166.0
        )))

    def test_load_multiple_annual_statements(self):
        self.givenAppleFinancials()

        self.whenTheSymbolIsFetched()

        assert_that(self.incomeStatementFor('AAPL', '2018-09-29'), equal_to(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            netIncome=59531000000.0,
            waso=5000109000
        )))

        assert_that(self.incomeStatementFor('AAPL', '2017-09-30'), equal_to(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            netIncome=48351000000.0,
            waso=5251692000
        )))

        assert_that(self.db.get_balance_sheet('AAPL', '2018-09-29'), equal_to(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )))

        assert_that(self.db.get_balance_sheet('AAPL', '2017-09-30'), equal_to(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        )))

    def test_dont_collide_with_existing(self):
        self.givenAppleFinancials()

        self.db.add_income(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            netIncome=59531000000.0,
            waso=5000109000
        ))

        self.db.add_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        ))

        self.db.add_income(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            netIncome=48351000000.0,
            waso=5251692000
        ))

        self.db.add_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        ))

        self.db.add_price(StockPrice(
            symbol='AAPL',
            date=datetime.date(2014, 6, 13),
            open=84.5035,
            high=84.7235,
            low=83.2937,
            close=83.6603,
            volume=5.452528E7
        ))

        self.whenTheSymbolIsFetched()

        assert_that(self.incomeStatementFor('AAPL', '2018-09-29'), equal_to(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            netIncome=59531000000.0,
            waso=5000109000
        )))

        assert_that(self.db.get_balance_sheet('AAPL', '2018-09-29'), equal_to(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )))

        assert_that(self.price_of('AAPL', to_date('2014-06-13')), equal_to(StockPrice(
            symbol='AAPL',
            date=datetime.date(2014, 6, 13),
            open=84.5035,
            high=84.7235,
            low=83.2937,
            close=83.6603,
            volume=5.452528E7
        )))


    def test_spy_has_no_financials(self):
        self.fin_gate.addSpyFinancials()

        self.whenTheSymbolIsFetched()

        self.assertEqual(self.db.income_statements, {})
        self.assertEqual(self.db.balance_sheets, {})

    def test_load_goog(self):
        self.givenGoogleFinancials()

        self.whenTheSymbolIsFetched(symbol='GOOG')

        assert_that(self.incomeStatementFor('GOOG', '2018-12-01'), equal_to(IncomeStatement(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            netIncome=30736000000.0,
            waso=750000000
        )))

        assert_that(self.db.get_balance_sheet('GOOG', '2018-12-01'), equal_to(BalanceSheet(
            symbol='GOOG',
            date=datetime.date(2018,12, 1),
            totalAssets=232792000000.0,
            totalLiabilities=1264000000.0
        )))

    def whenTheSymbolIsFetched(self, symbol: str = None):
        self.result = FinancialLoaderResult()
        self.result.on_load_symbol = self.capture_symbol
        self.loader.execute(FinancialLoaderRequest(symbol=symbol), self.result)

    def capture_symbol(self, symbol: str):
        self.symbols.append(symbol)

    def incomeStatementFor(self, symbol: str, date: str) -> IncomeStatement:
        return self.db.get_income_statement(symbol, date)

    def givenNvidiaFinancials(self):
        self.fin_gate.add_nvidia_financials()

    def givenGoogleFinancials(self):
        self.fin_gate.add_google_financials()

    def givenAppleFinancials(self):
        self.fin_gate.add_apple_financials()

    def givenNetflixFinancials(self):
        self.fin_gate.add_netflix_financials()

    def price_of(self, symbol: str, date: datetime.date) -> StockPrice:
        return self.db.get_price(symbol, date)
