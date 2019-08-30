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
