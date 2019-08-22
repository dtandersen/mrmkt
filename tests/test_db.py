import dataclasses
import unittest
from dataclasses import dataclass

import testing.postgresql
import psycopg2

from balance_sheet import BalanceSheet
from tests.test_load import FinancialRepository




class PgWrapper:
    def execute(self, query: dict):
        pass


class MockPgWrapper(PgWrapper):
    def __init__(self):
        self.commands = []

    def execute(self, query: dict):
        self.commands.append(query)


@dataclass
class BalanceSheetRow:
    symbol: str
    date: str
    total_assets: float
    total_liabilities: float

    # def __init__(self,
    #              symbol: str,
    #              date: str,
    #              total_assets: float,
    #              total_liabilities: float):
    #     self.symbol = symbol
    #     self.date = date
    #     self.total_assets = total_assets
    #     self.total_liabilities = total_liabilities

class PostgresFinancialRepository(FinancialRepository):
    def __init__(self, wrapper: PgWrapper):
        self.wrapper = wrapper

    def add_balance_sheet(self, balance_sheet: BalanceSheet):
        row = BalanceSheetRow(
            symbol=balance_sheet.symbol,
            date=balance_sheet.date,
            total_assets=balance_sheet.totalAssets,
            total_liabilities=balance_sheet.totalLiabilities
        )
        x = dataclasses.asdict(row)
        self.wrapper.execute(x)


class TestStringMethods(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_insert_balance(self):
        wrapper = MockPgWrapper()
        db = PostgresFinancialRepository(wrapper)
        db.add_balance_sheet(BalanceSheet(
            symbol='AAPL',
            date='20190813',
            totalAssets=10,
            totalLiabilities=25
        ))

        self.assertEqual(wrapper.commands[0], {
            "symbol": 'AAPL',
            "date": '20190813',
            "total_assets": 10,
            "total_liabilities": 25
        })
