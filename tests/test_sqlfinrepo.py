import datetime
import unittest
from entity.balance_sheet import BalanceSheet
from common.finrepo import SqlFinancialRepository, BalanceSheetRow, IncomeStatementRow, AnalysisRow, PriceRow
from entity.analysis import Analysis
from entity.income_statement import IncomeStatement
from common.sql import MockSqlClient
from entity.stock_price import StockPrice
from tests.canned import CannedData


class TestStringMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MockSqlClient()
        self.db = SqlFinancialRepository(self.client)
        self.canned = CannedData()

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
                             waso=5000109000
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
                             waso=625000000
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

        balance_sheets = self.db.get_balance_sheets("AAPL")
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

        balance_sheets = self.db.get_balance_sheets("NVDA")
        self.assertEqual(vars(balance_sheets[0]),
                         vars(BalanceSheet(
                             symbol='NVDA',
                             date=to_date('2019-01-27'),
                             totalAssets=13292000000.0,
                             totalLiabilities=3950000000.0
                         )))


def to_date(d: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(d)
    except ValueError:
        return datetime.date.fromisoformat(d + "-01")
