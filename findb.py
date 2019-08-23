import dataclasses
from dataclasses import dataclass

from balance_sheet import BalanceSheet
from income_statement import IncomeStatement
from postgres import SqlClient


class FinancialRepository:
    def add_income(self, income_statement: IncomeStatement) -> None:
        pass

    def add_balance_sheet(self, balance_sheet: BalanceSheet):
        pass


class InMemoryFinDb(FinancialRepository):
    income_statements = {}
    balance_sheets = {}

    def get_income_statement(self, symbol: str) -> IncomeStatement:
        return self.income_statements[symbol]

    def add_income(self, income_statement: IncomeStatement) -> None:
        self.income_statements[income_statement.symbol] = income_statement

    def add_balance_sheet(self, balance_sheet: BalanceSheet):
        self.balance_sheets[balance_sheet.symbol] = balance_sheet

    def get_balance_sheet(self, symbol: str) -> BalanceSheet:
        return self.balance_sheets[symbol]


class SqlFinancialRepository(FinancialRepository):
    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def add_balance_sheet(self, balance_sheet: BalanceSheet):
        row = BalanceSheetRow(
            symbol=balance_sheet.symbol,
            date=balance_sheet.date,
            total_assets=balance_sheet.totalAssets,
            total_liabilities=balance_sheet.totalLiabilities
        )
        self.sql_client.insert("balance_sheet", row)

    def add_income(self, income_statement: IncomeStatement):
        row = IncomeStatementRow(
            symbol=income_statement.symbol,
            date=income_statement.date,
            net_income=income_statement.netIncome,
            waso=income_statement.waso
        )
        self.sql_client.insert("income_stmt", row)


@dataclass
class BalanceSheetRow:
    symbol: str
    date: str
    total_assets: float
    total_liabilities: float


@dataclass
class IncomeStatementRow:
    symbol: str
    date: str
    net_income: float
    waso: int
