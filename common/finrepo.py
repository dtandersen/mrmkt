from abc import abstractmethod
from dataclasses import dataclass
from typing import List

from entity.balance_sheet import BalanceSheet
from entity.analysis import Analysis
from entity.income_statement import IncomeStatement
from common.sql import Duplicate, SqlClient


class FinancialRepository:
    @abstractmethod
    def get_income_statements(self, symbol: str) -> List[IncomeStatement]:
        pass

    @abstractmethod
    def get_income_statement(self, symbol: str, date: str) -> IncomeStatement:
        pass

    @abstractmethod
    def add_income(self, income_statement: IncomeStatement) -> None:
        pass

    @abstractmethod
    def get_balance_sheets(self, symbol: str) -> List[BalanceSheet]:
        pass

    @abstractmethod
    def get_balance_sheet(self, symbol: str, date: str) -> BalanceSheet:
        pass

    @abstractmethod
    def add_balance_sheet(self, balance_sheet: BalanceSheet) -> None:
        pass

    @abstractmethod
    def get_closing_price(self, symbol, date: str) -> float:
        pass

    @abstractmethod
    def add_close_price(self, symbol: str, date: str, price_close: float) -> None:
        pass

    @abstractmethod
    def add_analysis(self, analysis: Analysis):
        pass


class InMemoryFinancialRepository(FinancialRepository):
    def __init__(self):
        self.income_statements = {}
        self.balance_sheets = {}
        self.closing_prices = {}
        self.analysis = {}

    def get_income_statements(self, symbol: str) -> List[IncomeStatement]:
        return list(filter(lambda i: i.symbol == symbol, self.income_statements.values()))

    def get_income_statement(self, symbol: str, date: str) -> IncomeStatement:
        return self.income_statements[f"{symbol}-{date}"]

    def add_income(self, income_statement: IncomeStatement) -> None:
        if self.key(income_statement.symbol, income_statement.date) in self.income_statements:
            raise Duplicate("Duplicate: " + self.key(income_statement.symbol, income_statement.date))

        self.income_statements[f"{income_statement.symbol}-{income_statement.date}"] = income_statement

    def get_balance_sheets(self, symbol: str) -> List[BalanceSheet]:
        return list(filter(lambda i: i.symbol == symbol, self.balance_sheets.values()))

    def get_balance_sheet(self, symbol: str, date: str) -> BalanceSheet:
        return self.balance_sheets[f"{symbol}-{date}"]

    def add_balance_sheet(self, balance_sheet: BalanceSheet) -> None:
        if self.key(balance_sheet.symbol, balance_sheet.date) in self.balance_sheets:
            raise Duplicate("Duplicate: " + self.key(balance_sheet.symbol, balance_sheet.date))

        self.balance_sheets[f"{balance_sheet.symbol}-{balance_sheet.date}"] = balance_sheet

    def get_closing_price(self, symbol, date: str):
        return self.closing_prices[self.key(symbol, date)]

    def add_close_price(self, symbol: str, date: str, price_close: float):
        if self.key(symbol, date) in self.closing_prices:
            raise Duplicate("Duplicate: " + self.key(symbol, date))

        self.closing_prices[f"{symbol}-{date}"] = price_close

    def get_analysis(self, symbol: str) -> List[Analysis]:
        return [analysis for analysis in self.analysis.values() if analysis.symbol == symbol]

    def add_analysis(self, analysis: Analysis):
        self.analysis[self.key(analysis.symbol, analysis.date)] = analysis

    def key(self, symbol: str, date: str) -> str:
        return f"{symbol}-{date}"


class SqlFinancialRepository(FinancialRepository):
    def __init__(self, sql_client: SqlClient):
        self.sql_client = sql_client

    def get_balance_sheets(self, symbol: str):
        return self.sql_client.select("select * " +
                                      "from balance_sheet "
                                      f"where symbol = '{symbol}'",
                                      self.to_balance_sheet)

    def to_balance_sheet(self, row):
        return BalanceSheet(
            symbol=row["symbol"],
            date=row["date"],
            totalAssets=row["total_assets"],
            totalLiabilities=row["total_liabilities"])

    def add_balance_sheet(self, balance_sheet: BalanceSheet):
        row = BalanceSheetRow(
            symbol=balance_sheet.symbol,
            date=balance_sheet.date,
            total_assets=balance_sheet.totalAssets,
            total_liabilities=balance_sheet.totalLiabilities
        )

        self.sql_client.insert("balance_sheet", row)

    def get_income_statements(self, symbol: str) -> List[IncomeStatement]:
        return self.sql_client.select("select * " +
                                      "from income_stmt "
                                      f"where symbol = '{symbol}'",
                                      self.to_income_statement)

    def to_income_statement(self, row):
        return IncomeStatement(
            symbol=row["symbol"],
            date=row["date"],
            netIncome=row["net_income"],
            waso=row["waso"]
        )

    def add_income(self, income_statement: IncomeStatement):
        row = IncomeStatementRow(
            symbol=income_statement.symbol,
            date=income_statement.date,
            net_income=income_statement.netIncome,
            waso=income_statement.waso
        )

        self.sql_client.insert("income_stmt", row)

    def add_analysis(self, analysis: Analysis):
        row = AnalysisRow(
            symbol=analysis.symbol,
            date=analysis.date,
            net_income=analysis.netIncome,
            buffet_number=analysis.buffetNumber,
            price_to_book_value=analysis.priceToBookValue,
            shares_outstanding=analysis.sharesOutstanding,
            liabilities=analysis.liabilities,
            assets=analysis.assets,
            margin_of_safety=analysis.marginOfSafety,
            book_value=analysis.bookValue,
            eps=analysis.eps,
            equity=analysis.equity,
            pe=analysis.pe
        )

        self.sql_client.insert("analysis", row)


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


@dataclass
class AnalysisRow:
    symbol: str
    date: str
    net_income: float
    buffet_number: float
    price_to_book_value: float
    shares_outstanding: float
    liabilities: float
    assets: float
    margin_of_safety: float
    book_value: float
    eps: float
    equity: float
    pe: float
