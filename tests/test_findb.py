import unittest
from balance_sheet import BalanceSheet
from findb import SqlFinancialRepository, BalanceSheetRow, IncomeStatementRow
from income_statement import IncomeStatement
from sql import MockSqlClient


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
