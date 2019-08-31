import unittest
from entity.balance_sheet import BalanceSheet
from common.finrepo import SqlFinancialRepository, BalanceSheetRow, IncomeStatementRow, AnalysisRow
from entity.analysis import Analysis
from entity.income_statement import IncomeStatement
from common.sql import MockSqlClient


class TestStringMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MockSqlClient()
        self.db = SqlFinancialRepository(self.client)

    def test_insert_balance(self):
        self.db.add_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date='20190813',
            totalAssets=10,
            totalLiabilities=25
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "balance_sheet",
            "values": BalanceSheetRow(
                symbol='AAPL',
                date='20190813',
                total_assets=10,
                total_liabilities=25
            )
        }])

    def test_insert_income_stmt(self):
        self.db.add_income(IncomeStatement(
            symbol='AAPL',
            date='20190813',
            netIncome=10,
            waso=50,
        ))

        self.assertEqual(self.client.inserts, [{
            "table": "income_stmt",
            "values": IncomeStatementRow(
                symbol='AAPL',
                date='20190813',
                net_income=10,
                waso=50,
            )
        }])

    def test_insert_analysis(self):
        self.db.add_analysis(Analysis(
            symbol='AAPL',
            date='2019-08-25',
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
                date='2019-08-25',
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

    def test_get_income_statement(self):
        self.client.append_select("select * " +
                                  "from income_stmt "
                                  "where symbol = 'AAPL'",
                                  [
                                      IncomeStatementRow(
                                          symbol='AAPL',
                                          date='2018-09-29',
                                          net_income=59531000000.0,
                                          waso=5000109000
                                      ),
                                      IncomeStatementRow(
                                          symbol='AAPL',
                                          date='2017-09-30',
                                          net_income=48351000000.0,
                                          waso=5251692000
                                      )
                                  ])

        income_statements = self.db.get_income_statements("AAPL")
        self.assertEqual(vars(income_statements[0]),
                         vars(IncomeStatement(
                             symbol='AAPL',
                             date='2018-09-29',
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
                                          date='2019-01-27',
                                          net_income=4141000000.0,
                                          waso=625000000
                                      )
                                  ])

        income_statements = self.db.get_income_statements("NVDA")
        self.assertEqual(vars(income_statements[0]),
                         vars(IncomeStatement(
                             symbol='NVDA',
                             date='2019-01-27',
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
                                          date='2018-09-29',
                                          total_assets=365725000000.0,
                                          total_liabilities=258578000000.0
                                      ),
                                      BalanceSheetRow(
                                          symbol='AAPL',
                                          date='2017-09-30',
                                          total_assets=375319000000.0,
                                          total_liabilities=241272000000.0
                                      )
                                  ])

        balance_sheets = self.db.get_balance_sheets("AAPL")
        self.assertEqual(vars(balance_sheets[0]),
                         vars(BalanceSheet(
                             symbol='AAPL',
                             date='2018-09-29',
                             totalAssets =365725000000.0,
                             totalLiabilities=258578000000
                         )))
        self.assertEqual(vars(balance_sheets[1]),
                         vars(BalanceSheet(
                             symbol='AAPL',
                             date='2017-09-30',
                             totalAssets =375319000000.0,
                             totalLiabilities=241272000000
                         )))

    def test_get_balance_sheet2(self):
        self.client.append_select("select * " +
                                  "from balance_sheet "
                                  "where symbol = 'NVDA'",
                                  [
                                      BalanceSheetRow(
                                          symbol='NVDA',
                                          date='2019-01-27',
                                          total_assets=13292000000.0,
                                          total_liabilities=3950000000.0
                                      )
                                  ])

        balance_sheets = self.db.get_balance_sheets("NVDA")
        self.assertEqual(vars(balance_sheets[0]),
                         vars(BalanceSheet(
                             symbol='NVDA',
                             date='2019-01-27',
                             totalAssets =13292000000.0,
                             totalLiabilities=3950000000.0
                         )))
