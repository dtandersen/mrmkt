import unittest
from balance_sheet import BalanceSheet
from findb import SqlFinancialRepository, BalanceSheetRow
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
