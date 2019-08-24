from dataclasses import dataclass
from balance_sheet import BalanceSheet
from income_statement import IncomeStatement
from postgres import SqlClient
from sql import Duplicate


class FinancialRepository:
    def add_income(self, income_statement: IncomeStatement) -> None:
        pass

    def add_balance_sheet(self, balance_sheet: BalanceSheet) -> None:
        pass


class InMemoryFinancialRepository(FinancialRepository):
    def __init__(self):
        self.income_statements = {}
        self.balance_sheets = {}

    def get_income_statement(self, symbol: str, date: str) -> IncomeStatement:
        return self.income_statements[f"{symbol}-{date}"]

    def add_income(self, income_statement: IncomeStatement) -> None:
        if self.key(income_statement.symbol, income_statement.date) in self.income_statements:
            raise Duplicate("Duplicate: " + self.key(income_statement.symbol, income_statement.date))

        self.income_statements[f"{income_statement.symbol}-{income_statement.date}"] = income_statement

    def get_balance_sheet(self, symbol: str, date: str) -> BalanceSheet:
        return self.balance_sheets[f"{symbol}-{date}"]

    def add_balance_sheet(self, balance_sheet: BalanceSheet) -> None:
        if self.key(balance_sheet.symbol, balance_sheet.date) in self.balance_sheets:
            raise Duplicate("Duplicate: " + self.key(balance_sheet.symbol, balance_sheet.date))

        self.balance_sheets[f"{balance_sheet.symbol}-{balance_sheet.date}"] = balance_sheet

    def key(self, symbol: str, date: str) -> str:
        return f"{symbol}-{date}"


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
