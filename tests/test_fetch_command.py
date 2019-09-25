import datetime
import unittest
from typing import List

from hamcrest import *

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.common.testfinrepo import FinancialTestRepository
from mrmkt.common.util import to_date
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.usecase.fetch import FinancialLoader, FinancialLoaderRequest, FinancialLoaderResult


class TestFetch(unittest.TestCase):
    symbols: List[str]

    def setUp(self) -> None:
        self.sourcerepo = FinancialTestRepository()
        self.destrepo = InMemoryFinancialRepository()
        self.loader = FinancialLoader(self.sourcerepo, self.destrepo)
        self.symbols = []

    def test_load_two_symbols(self):
        self.given_source_has_netflix_financials()
        self.given_source_has_nvidia_financials()

        self.when_the_symbol_is_fetched()

        assert_that(self.symbols, equal_to(['NFLX', 'NVDA']))

        assert_that(self.dest_income_statement('NFLX', '2018-12-31'), equal_to(IncomeStatement(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            netIncome=1211242000.0,
            waso=451244000,
            consolidated_net_income=-1
        )))

        assert_that(self.dest_balance_sheet('NFLX', '2018-12-31'), equal_to(BalanceSheet(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            totalAssets=25974400000.0,
            totalLiabilities=20735635000.0)))

        assert_that(self.dest_cash_flow('NFLX', '2018-12-31'), equal_to(self.source_cash_flow('NFLX', '2018-12-31')))
        assert_that(self.dest_enterprise_value('NFLX', '2018-12-31'),
                    equal_to(self.source_enterprise_value('NFLX', '2018-12-31')))

        assert_that(self.dest_income_statement('NVDA', '2019-01-27'), equal_to(IncomeStatement(
            symbol='NVDA',
            date=datetime.date(2019, 1, 27),
            netIncome=4141000000.0,
            waso=625000000,
            consolidated_net_income=-1
        )))

        assert_that(self.dest_balance_sheet('NVDA', '2019-01-27'), equal_to(BalanceSheet(
            symbol='NVDA',
            date=datetime.date(2019, 1, 27),
            totalAssets=13292000000.0,
            totalLiabilities=3950000000.0
        )))

        assert_that(self.dest_price('NVDA', to_date('2014-06-13')), equal_to(StockPrice(
            symbol='NVDA',
            date=datetime.date(2014, 6, 13),
            open=18.8814,
            high=18.891,
            low=18.5272,
            close=18.7091,
            volume=5696281.0
        )))

    def test_load_multiple_annual_statements(self):
        self.given_source_has_apple_financials()

        self.when_the_symbol_is_fetched()

        assert_that(self.dest_income_statement('AAPL', '2018-09-29'), equal_to(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            netIncome=59531000000.0,
            waso=5000109000,
            consolidated_net_income=-1
        )))

        assert_that(self.dest_income_statement('AAPL', '2017-09-30'), equal_to(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            netIncome=48351000000.0,
            waso=5251692000,
            consolidated_net_income=-1
        )))

        assert_that(self.dest_balance_sheet('AAPL', '2018-09-29'), equal_to(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )))

        assert_that(self.dest_balance_sheet('AAPL', '2017-09-30'), equal_to(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        )))

    def test_google_dates_with_no_day(self):
        self.given_source_has_google_financials()

        self.when_the_symbol_is_fetched('GOOG')

        self.assertEqual(self.symbols, ['GOOG'])

        assert_that(self.dest_income_statement('GOOG', '2018-12-01'), equal_to(IncomeStatement(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            netIncome=30736000000.0,
            waso=750000000,
            consolidated_net_income=-1
        )))

        assert_that(self.dest_balance_sheet('GOOG', '2018-12-01'), equal_to(BalanceSheet(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            totalAssets=232792000000.0,
            totalLiabilities=1264000000.0)))

        assert_that(self.dest_price('GOOG', to_date('2018-11-30')), equal_to(StockPrice(
            symbol='GOOG',
            date=datetime.date(2018, 11, 30),
            open=1089.07,
            high=1095.57,
            low=1077.88,
            close=1094.43,
            volume=2580612.0
        )))
        assert_that(self.dest_price('GOOG', to_date('2018-12-03')), equal_to(StockPrice(
            symbol='GOOG',
            date=datetime.date(2018, 12, 3),
            open=1103.12,
            high=1104.42,
            low=1049.98,
            close=1050.82,
            volume=2345166.0
        )))

    def test_dont_collide_with_existing(self):
        self.given_source_has_apple_financials()

        self.given_dest_has_existing_income_statement(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            netIncome=59531000000.0,
            waso=5000109000,
            consolidated_net_income=-1
        ))

        self.given_dest_has_existing_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0))

        self.when_dest_contains_same_cash_flow_as_source('AAPL', '2018-09-29')
        self.when_dest_contains_same_enterprise_value_as_source('AAPL', '2018-09-29')

        self.given_dest_has_existing_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        ))

        self.given_dest_has_price(StockPrice(
            symbol='AAPL',
            date=datetime.date(2014, 6, 13),
            open=84.5035,
            high=84.7235,
            low=83.2937,
            close=83.6603,
            volume=5.452528E7))

        self.when_the_symbol_is_fetched()

        assert_that(self.dest_income_statement('AAPL', '2018-09-29'), equal_to(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            netIncome=59531000000.0,
            waso=5000109000,
            consolidated_net_income=-1
        )))

        assert_that(self.dest_balance_sheet('AAPL', '2018-09-29'), equal_to(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )))

        assert_that(self.dest_cash_flow('AAPL', '2018-09-29'), equal_to(self.source_cash_flow('AAPL', '2018-09-29')))
        assert_that(self.dest_enterprise_value('AAPL', '2018-09-29'),
                    equal_to(self.source_enterprise_value('AAPL', '2018-09-29')))

        assert_that(self.dest_price('AAPL', to_date('2014-06-13')), equal_to(StockPrice(
            symbol='AAPL',
            date=datetime.date(2014, 6, 13),
            open=84.5035,
            high=84.7235,
            low=83.2937,
            close=83.6603,
            volume=5.452528E7
        )))

    def test_spy_has_no_financials(self):
        self.given_source_has_spy_financials()

        self.when_the_symbol_is_fetched()

        self.assertEqual(self.destrepo.incomes.size(), 0)
        self.assertEqual(self.destrepo.balances.size(), 0)
        self.assertEqual(self.destrepo.cashflows.size(), 0)
        self.assertEqual(self.destrepo.enterprises.size(), 0)

    def when_dest_contains_same_cash_flow_as_source(self, symbol, date):
        self.given_dest_has_existing_cash_flow(self.source_cash_flow(symbol, date))

    def when_dest_contains_same_enterprise_value_as_source(self, symbol, date):
        self.given_dest_has_existing_enterprise_value(self.source_enterprise_value(symbol, date))

    def given_source_has_spy_financials(self):
        self.sourcerepo.addSpyFinancials()

    def given_dest_has_price(self, price):
        self.destrepo.add_price(price)

    def given_dest_has_existing_balance_sheet(self, sheet):
        self.destrepo.add_balance_sheet(sheet)

    def given_dest_has_existing_income_statement(self, statement):
        self.destrepo.add_income(statement)

    def given_dest_has_existing_cash_flow(self, cash_flow: CashFlow):
        self.destrepo.add_cash_flow(cash_flow)

    def given_dest_has_existing_enterprise_value(self, enterprise_value: EnterpriseValue):
        self.destrepo.add_enterprise_value(enterprise_value)

    def when_the_symbol_is_fetched(self, symbol: str = None):
        self.result = FinancialLoaderResult()
        self.result.on_load_symbol = self.capture_symbol
        self.loader.execute(FinancialLoaderRequest(symbol=symbol), self.result)

    def capture_symbol(self, symbol: str):
        self.symbols.append(symbol)

    def dest_income_statement(self, symbol: str, date: str) -> IncomeStatement:
        return self.destrepo.get_income_statement(symbol, to_date(date))

    def given_source_has_nvidia_financials(self):
        self.sourcerepo.add_nvidia_financials()

    def given_source_has_google_financials(self):
        self.sourcerepo.add_google_financials()

    def given_source_has_apple_financials(self):
        self.sourcerepo.add_apple_financials()

    def given_source_has_netflix_financials(self):
        self.sourcerepo.add_netflix_financials()

    def dest_price(self, symbol: str, date: datetime.date) -> StockPrice:
        return self.destrepo.get_price(symbol, date)

    def dest_balance_sheet(self, nflx, s):
        return self.destrepo.get_balance_sheet(nflx, s)

    def source_cash_flow(self, symbol: str, date: str) -> CashFlow:
        return self.sourcerepo.get_cash_flow(symbol, to_date(date))

    def dest_cash_flow(self, symbol: str, date: str) -> CashFlow:
        return self.destrepo.get_cash_flow(symbol, to_date(date))

    def source_enterprise_value(self, symbol: str, date: str) -> EnterpriseValue:
        return self.sourcerepo.get_enterprise_value(symbol, to_date(date))

    def dest_enterprise_value(self, symbol: str, date: str) -> EnterpriseValue:
        return self.destrepo.get_enterprise_value(symbol, to_date(date))
