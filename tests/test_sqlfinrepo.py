import datetime
import unittest
from hamcrest import *

from mrmkt.common.sql import MockSqlClient
from mrmkt.common.sqlfinrepo import SqlFinancialRepository, BalanceSheetRow, IncomeStatementRow, AnalysisRow, \
    CashFlowRow, EnterpriseValueRow, PriceRow, SymbolRow, TickerRow
from mrmkt.common.testfinrepo import FinancialTestRepository
from mrmkt.common.util import to_date
from mrmkt.entity.analysis import Analysis
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker


class TestStringMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MockSqlClient()
        self.db = SqlFinancialRepository(self.client)
        self.canned = FinancialTestRepository().with_all()

    def test_insert_balance(self):
        self.db.add_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date=to_date('2019-08-13'),
            totalAssets=10,
            totalLiabilities=25
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "balance_sheet",
            "values": BalanceSheetRow(
                symbol='AAPL',
                date=to_date('2019-08-13'),
                total_assets=10,
                total_liabilities=25
            )
        }])

    def test_insert_income_stmt(self):
        self.db.add_income(IncomeStatement(
            symbol='AAPL',
            date=to_date('2019-08-13'),
            netIncome=10,
            waso=50,
            consolidated_net_income=-1
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "income_stmt",
            "values": IncomeStatementRow(
                symbol='AAPL',
                date=to_date('2019-08-13'),
                net_income=10,
                waso=50,
            )
        }])

    def test_insert_analysis(self):
        self.db.add_analysis(Analysis(
            symbol='AAPL',
            date=to_date('2019-08-25'),
            netIncome=1,
            buffetNumber=2,
            priceToBookValue=3,
            sharesOutstanding=4,
            liabilities=5,
            assets=6,
            marginOfSafety=7,
            bookValue=8,
            eps=9,
            equity=10,
            pe=11
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "analysis",
            "values": AnalysisRow(
                symbol='AAPL',
                date=to_date('2019-08-25'),
                net_income=1,
                buffet_number=2,
                price_to_book_value=3,
                shares_outstanding=4,
                liabilities=5,
                assets=6,
                margin_of_safety=7,
                book_value=8,
                eps=9,
                equity=10,
                pe=11
            )
        }])

    def test_delete_analysis(self):
        self.db.delete_analysis('ABC', to_date('2019-01-02'))

        self.assertEqual(self.client.queries, [
            "delete from analysis "
            "where symbol = 'ABC' "
            "and date = '2019-01-02'"
        ])

    def test_delete_analysis2(self):
        self.db.delete_analysis('XYZ', to_date('2018-12-11'))

        self.assertEqual(self.client.queries, [
            "delete from analysis "
            "where symbol = 'XYZ' "
            "and date = '2018-12-11'"
        ])

    def test_get_price(self):
        self.client.append_select("select * " +
                                  "from daily_price "
                                  "where symbol = 'GOOG' "
                                  "and date = '2014-06-13'",
                                  [PriceRow(
                                      symbol='GOOG',
                                      date=datetime.date(2014, 6, 13),
                                      open=552.26,
                                      high=552.3,
                                      low=545.56,
                                      close=551.76,
                                      volume=1217176.0
                                  )])

        price = self.db.get_price("GOOG", "2014-06-13")
        self.assertEqual(vars(price),
                         vars(StockPrice(
                             symbol='GOOG',
                             date=datetime.date(2014, 6, 13),
                             open=552.26,
                             high=552.3,
                             low=545.56,
                             close=551.76,
                             volume=1217176.0
                         )))

    def test_get_price2(self):
        self.client.append_select("select * " +
                                  "from daily_price "
                                  "where symbol = 'AAPL' "
                                  "and date = '2014-06-16'",
                                  [PriceRow(
                                      symbol='AAPL',
                                      date=datetime.date(2014, 6, 16),
                                      open=83.8711,
                                      high=85.0076,
                                      low=83.8161,
                                      close=84.5035,
                                      volume=3.556127E7
                                  )])

        price = self.db.get_price("AAPL", "2014-06-16")
        self.assertEqual(vars(price),
                         vars(StockPrice(
                             symbol='AAPL',
                             date=datetime.date(2014, 6, 16),
                             open=83.8711,
                             high=85.0076,
                             low=83.8161,
                             close=84.5035,
                             volume=3.556127E7
                         )))

    def test_list_prices(self):
        self.client.append_select(
            "select * " +
            "from daily_price "
            "where symbol = 'GOOG' "
            "order by date asc",
            [
                PriceRow(
                    symbol='GOOG',
                    date=datetime.date(2014, 6, 13),
                    open=552.26,
                    high=552.3,
                    low=545.56,
                    close=551.76,
                    volume=1217176.0
                ),
                PriceRow(
                    symbol='GOOG',
                    date=datetime.date(2014, 6, 16),
                    open=549.26,
                    high=549.62,
                    low=541.52,
                    close=544.28,
                    volume=1704027.0
                )])

        prices = self.db.list_prices("GOOG")
        assert_that(prices, equal_to([
            StockPrice(
                symbol='GOOG',
                date=datetime.date(2014, 6, 13),
                open=552.26,
                high=552.3,
                low=545.56,
                close=551.76,
                volume=1217176.0
            ), StockPrice(
                symbol='GOOG',
                date=datetime.date(2014, 6, 16),
                open=549.26,
                high=549.62,
                low=541.52,
                close=544.28,
                volume=1704027.0
            )
        ]))

    def test_list_prices2(self):
        self.client.append_select(
            "select * " +
            "from daily_price "
            "where symbol = 'AAPL' "
            "order by date asc",
            [
                PriceRow(
                    symbol='AAPL',
                    date=datetime.date(2019, 9, 23),
                    open=218.73,
                    high=219.575,
                    low=218.73,
                    close=218.94,
                    volume=1.7990369E7
                )])

        prices = self.db.list_prices("AAPL")
        assert_that(prices, equal_to([
            StockPrice(
                symbol='AAPL',
                date=datetime.date(2019, 9, 23),
                open=218.73,
                high=219.575,
                low=218.73,
                close=218.94,
                volume=1.7990369E7
            )]))

    def test_get_price_on_or_after2(self):
        self.client.append_select("select * " +
                                  "from daily_price "
                                  "where symbol = 'AAPL' "
                                  "and date >= '2014-06-15' "
                                  "order by date asc",
                                  [PriceRow(
                                      symbol='AAPL',
                                      date=datetime.date(2014, 6, 16),
                                      open=83.8711,
                                      high=85.0076,
                                      low=83.8161,
                                      close=84.5035,
                                      volume=3.556127E7
                                  )])

        prices = self.db.list_prices("AAPL", start=to_date("2014-06-15"))
        assert_that(prices, equal_to(
            [StockPrice(
                symbol='AAPL',
                date=datetime.date(2014, 6, 16),
                open=83.8711,
                high=85.0076,
                low=83.8161,
                close=84.5035,
                volume=3.556127E7)
            ]))

    def test_get_price_on_or_before(self):
        self.client.append_select("select * " +
                                  "from daily_price "
                                  "where symbol = 'AAPL' "
                                  "and date <= '2014-06-15' "
                                  "order by date asc",
                                  [PriceRow(
                                      symbol='AAPL',
                                      date=datetime.date(2014, 6, 16),
                                      open=83.8711,
                                      high=85.0076,
                                      low=83.8161,
                                      close=84.5035,
                                      volume=3.556127E7
                                  )])

        prices = self.db.list_prices("AAPL", end=to_date("2014-06-15"))
        assert_that(prices, equal_to(
            [StockPrice(
                symbol='AAPL',
                date=datetime.date(2014, 6, 16),
                open=83.8711,
                high=85.0076,
                low=83.8161,
                close=84.5035,
                volume=3.556127E7)
            ]))

    def test_get_price_on_or_after(self):
        self.client.append_select("select * " +
                                  "from daily_price "
                                  "where symbol = 'AAPL' "
                                  "and date >= '2014-06-15'",
                                  [PriceRow(
                                      symbol='AAPL',
                                      date=datetime.date(2014, 6, 16),
                                      open=83.8711,
                                      high=85.0076,
                                      low=83.8161,
                                      close=84.5035,
                                      volume=3.556127E7
                                  )])

        price = self.db.get_price_on_or_after("AAPL", "2014-06-15")
        self.assertEqual(vars(price),
                         vars(StockPrice(
                             symbol='AAPL',
                             date=datetime.date(2014, 6, 16),
                             open=83.8711,
                             high=85.0076,
                             low=83.8161,
                             close=84.5035,
                             volume=3.556127E7
                         )))

    def test_insert_price(self):
        self.db.add_price(self.canned.get_price('GOOG', datetime.date(2014, 6, 13)))

        self.assertEqual(self.client.inserts, [{
            "table": "daily_price",
            "values": PriceRow(
                symbol='GOOG',
                date=datetime.date(2014, 6, 13),
                open=552.26,
                high=552.3,
                low=545.56,
                close=551.76,
                volume=1217176.0
            )
        }])

    def test_get_income_statement(self):
        self.client.append_select("select * " +
                                  "from income_stmt "
                                  "where symbol = 'AAPL'",
                                  [
                                      IncomeStatementRow(
                                          symbol='AAPL',
                                          date=datetime.date(2018, 9, 29),
                                          net_income=59531000000.0,
                                          waso=5000109000
                                      ),
                                      IncomeStatementRow(
                                          symbol='AAPL',
                                          date=datetime.datetime.strptime('2017-09-30', '%Y-%m-%d'),
                                          net_income=48351000000.0,
                                          waso=5251692000
                                      )
                                  ])

        income_statements = self.db.get_income_statements("AAPL")
        self.assertEqual(vars(income_statements[0]),
                         vars(IncomeStatement(
                             symbol='AAPL',
                             date=to_date('2018-09-29'),
                             netIncome=59531000000.0,
                             waso=5000109000,
                             consolidated_net_income=-1
                         )))

    def test_get_income_statement2(self):
        self.client.append_select("select * " +
                                  "from income_stmt "
                                  "where symbol = 'NVDA'",
                                  [
                                      IncomeStatementRow(
                                          symbol='NVDA',
                                          date=to_date('2019-01-27'),
                                          net_income=4141000000.0,
                                          waso=625000000
                                      )
                                  ])

        income_statements = self.db.get_income_statements("NVDA")
        self.assertEqual(vars(income_statements[0]),
                         vars(IncomeStatement(
                             symbol='NVDA',
                             date=to_date('2019-01-27'),
                             netIncome=4141000000.0,
                             waso=625000000,
                             consolidated_net_income=-1
                         )))

    def test_get_balance_sheet(self):
        self.client.append_select("select * " +
                                  "from balance_sheet "
                                  "where symbol = 'AAPL'",
                                  [
                                      BalanceSheetRow(
                                          symbol='AAPL',
                                          date=to_date('2018-09-29'),
                                          total_assets=365725000000.0,
                                          total_liabilities=258578000000.0
                                      ),
                                      BalanceSheetRow(
                                          symbol='AAPL',
                                          date=to_date('2017-09-30'),
                                          total_assets=375319000000.0,
                                          total_liabilities=241272000000.0
                                      )
                                  ])

        balance_sheets = self.db.list_balance_sheets("AAPL")
        self.assertEqual(vars(balance_sheets[0]),
                         vars(BalanceSheet(
                             symbol='AAPL',
                             date=to_date('2018-09-29'),
                             totalAssets=365725000000.0,
                             totalLiabilities=258578000000
                         )))
        self.assertEqual(vars(balance_sheets[1]),
                         vars(BalanceSheet(
                             symbol='AAPL',
                             date=to_date('2017-09-30'),
                             totalAssets=375319000000.0,
                             totalLiabilities=241272000000
                         )))

    def test_get_balance_sheet2(self):
        self.client.append_select("select * " +
                                  "from balance_sheet "
                                  "where symbol = 'NVDA'",
                                  [
                                      BalanceSheetRow(
                                          symbol='NVDA',
                                          date=to_date('2019-01-27'),
                                          total_assets=13292000000.0,
                                          total_liabilities=3950000000.0
                                      )
                                  ])

        balance_sheets = self.db.list_balance_sheets("NVDA")
        self.assertEqual(vars(balance_sheets[0]),
                         vars(BalanceSheet(
                             symbol='NVDA',
                             date=to_date('2019-01-27'),
                             totalAssets=13292000000.0,
                             totalLiabilities=3950000000.0
                         )))

    # def test_insert_financial(self):
    #     inc = self.canned.get_income_statement("AAPL", to_date("2018-09-29"))
    #     bs = self.canned.get_balance_sheet("AAPL",  to_date("2018-09-29"))
    #     cf = self.canned.get_cash_flow("AAPL",  to_date("2018-09-29"))
    #     rep = FinancialReport(
    #         symbol="AAPL",
    #         date=datetime.date(2018, 9, 29),
    #         income_statement=inc,
    #         balance_sheet=bs,
    #         cash_flow=cf)
    #     self.db.insert_financial(rep)
    #
    #     assert_that(self.client.inserts2[0]['table'], equal_to("financials"))
    #     assert_that(self.client.inserts2[0]['values'], equal_to(FinancialRow(
    #         symbol="abc",
    #         date=datetime.date(2019, 1, 2),
    #         data=json.dumps(rep, cls=EnhancedJSONEncoder)
    #     )))

    def test_get_cash_flow(self):
        self.client.append_select("select * " +
                                  "from cash_flow "
                                  "where symbol = 'a' "
                                  "and date = '2019-01-02'",
                                  [
                                      CashFlowRow(
                                          symbol='a',
                                          date=to_date('2019-01-02'),
                                          operating_cash_flow=1,
                                          capital_expenditure=2,
                                          free_cash_flow=3,
                                          dividend_payments=4
                                      )
                                  ])

        cash_flow = self.db.get_cash_flow("a", to_date('2019-01-02'))
        self.assertEqual(vars(cash_flow),
                         vars(CashFlow(
                             symbol='a',
                             date=to_date('2019-01-02'),
                             operating_cash_flow=1,
                             capital_expenditure=2,
                             free_cash_flow=3,
                             dividend_payments=4
                         )))

    def test_get_cash_flow2(self):
        self.client.append_select(
            "select * " +
            "from cash_flow "
            "where symbol = 'b' "
            "and date = '2018-12-31'",
            [CashFlowRow(
                symbol='b',
                date=to_date('2018-12-31'),
                operating_cash_flow=9,
                capital_expenditure=8,
                free_cash_flow=7,
                dividend_payments=6
            )])

        cash_flow = self.db.get_cash_flow("b", to_date('2018-12-31'))
        self.assertEqual(
            vars(cash_flow),
            vars(CashFlow(
                symbol='b',
                date=to_date('2018-12-31'),
                operating_cash_flow=9,
                capital_expenditure=8,
                free_cash_flow=7,
                dividend_payments=6
            )))

    def test_add_cash_flow(self):
        self.db.add_cash_flow(CashFlow(
            symbol='a',
            date=to_date('2019-01-02'),
            operating_cash_flow=1,
            capital_expenditure=2,
            free_cash_flow=3,
            dividend_payments=4
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "cash_flow",
            "values": CashFlowRow(
                symbol='a',
                date=to_date('2019-01-02'),
                operating_cash_flow=1,
                capital_expenditure=2,
                free_cash_flow=3,
                dividend_payments=4
            )
        }])

    def test_add_cash_flow2(self):
        self.db.add_cash_flow(CashFlow(
            symbol='b',
            date=to_date('2018-12-31'),
            operating_cash_flow=4,
            capital_expenditure=3,
            free_cash_flow=2,
            dividend_payments=1
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "cash_flow",
            "values": CashFlowRow(
                symbol='b',
                date=to_date('2018-12-31'),
                operating_cash_flow=4,
                capital_expenditure=3,
                free_cash_flow=2,
                dividend_payments=1
            )
        }])

    def test_get_get_enterprise_value(self):
        self.client.append_select(
            "select * " +
            "from enterprise_value "
            "where symbol = 'a' "
            "and date = '2019-01-02'",
            [EnterpriseValueRow(
                symbol='a',
                date=to_date('2019-01-02'),
                stock_price=1,
                shares_outstanding=2,
                market_cap=3
            )])

        enterprise_value = self.db.get_enterprise_value("a", to_date('2019-01-02'))
        self.assertEqual(
            vars(enterprise_value),
            vars(EnterpriseValue(
                symbol='a',
                date=to_date('2019-01-02'),
                stock_price=1,
                shares_outstanding=2,
                market_cap=3
            )))

    def test_get_get_enterprise_value2(self):
        self.client.append_select(
            "select * " +
            "from enterprise_value "
            "where symbol = 'b' "
            "and date = '2018-12-31'",
            [EnterpriseValueRow(
                symbol='b',
                date=to_date('2018-12-31'),
                stock_price=9,
                shares_outstanding=8,
                market_cap=7
            )])

        enterprise_value = self.db.get_enterprise_value("b", to_date('2018-12-31'))
        self.assertEqual(
            vars(enterprise_value),
            vars(EnterpriseValue(
                symbol='b',
                date=to_date('2018-12-31'),
                stock_price=9,
                shares_outstanding=8,
                market_cap=7
            )))

    def test_add_enterprise_value(self):
        self.db.add_enterprise_value(EnterpriseValue(
            symbol='a',
            date=to_date('2019-01-02'),
            stock_price=1,
            shares_outstanding=2,
            market_cap=3
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "enterprise_value",
            "values": EnterpriseValueRow(
                symbol='a',
                date=to_date('2019-01-02'),
                stock_price=1,
                shares_outstanding=2,
                market_cap=3
            )
        }])

    def test_add_enterprise_value2(self):
        self.db.add_enterprise_value(EnterpriseValue(
            symbol='a',
            date=to_date('2018-12-31'),
            stock_price=9,
            shares_outstanding=8,
            market_cap=7
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "enterprise_value",
            "values": EnterpriseValueRow(
                symbol='a',
                date=to_date('2018-12-31'),
                stock_price=9,
                shares_outstanding=8,
                market_cap=7
            )
        }])

    def test_get_symbols(self):
        self.client.append_select(
            "select distinct symbol " +
            "from daily_price ",
            [SymbolRow(symbol='ABC'), SymbolRow(symbol='XYZ')])

        prices = self.db.get_symbols()
        assert_that(prices, equal_to(['ABC', 'XYZ']))

    def test_get_tickers(self):
        self.client.append_select(
            "select * " +
            "from ticker",
            [
                TickerRow(
                    ticker='ABC',
                    exchange='NYSE ARCA',
                    type='ETF'
                ),
                TickerRow(
                    ticker='XYZ',
                    exchange='NASDAQ',
                    type='Stock'
                )
            ])

        prices = self.db.get_tickers()
        assert_that(prices, equal_to([
            Ticker(
                ticker='ABC',
                exchange='NYSE ARCA',
                type='ETF'
            ),
            Ticker(
                ticker='XYZ',
                exchange='NASDAQ',
                type='Stock'
            )
        ]))

    def test_add_ticker(self):
        self.db.add_ticker(Ticker(
            ticker='ABC',
            exchange='NYSE ARCA',
            type='ETF'
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "ticker",
            "values": TickerRow(
                ticker='ABC',
                exchange='NYSE ARCA',
                type='ETF'
            )
        }])
