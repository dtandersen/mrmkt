import datetime
from abc import abstractmethod
from dataclasses import dataclass
from typing import List

from entity.balance_sheet import BalanceSheet
from entity.analysis import Analysis
from entity.income_statement import IncomeStatement
from common.sql import Duplicate, SqlClient
from entity.stock_price import StockPrice


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
    def add_analysis(self, analysis: Analysis):
        pass

    @abstractmethod
    def get_price(self, symbol: str, date: str) -> StockPrice:
        pass

    @abstractmethod
    def add_price(self, price: StockPrice):
        pass


class InMemoryFinancialRepository(FinancialRepository):
    def __init__(self):
        self.income_statements = {}
        self.balance_sheets = {}
        self.analysis = {}
        self.prices = {}
        self.stocks = []

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

    def add_close_price(self, symbol: str, date: datetime.date, price_close: float):
        self.add_price(StockPrice(
            symbol=symbol,
            date=date,
            close=price_close,
            open=0,
            high=0,
            low=0,
            volume=0
            ))

    def get_analysis(self, symbol: str) -> List[Analysis]:
        return [analysis for analysis in self.analysis.values() if analysis.symbol == symbol]

    def add_analysis(self, analysis: Analysis):
        self.analysis[self.key(analysis.symbol, analysis.date)] = analysis

    def key(self, symbol: str, date: datetime.date) -> str:
        d = date.strftime("%Y-%m-%d")
        # d = datetime.date.fromisoformat()
        return f"{symbol}-{d}"

    def add_price(self, price: StockPrice):
        if self.key(price.symbol, price.date) in self.prices:
            raise Duplicate("Duplicate: " + self.key(price.symbol, price.date))

        self.prices[self.key(price.symbol, price.date)] = price

    def get_price(self, symbol, date: datetime.date):
        return self.prices[self.key(symbol, date)]


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

    def add_price(self, price: StockPrice):
        row = PriceRow(
            symbol=price.symbol,
            date=price.date,
            open=price.open,
            high=price.high,
            low=price.low,
            close=price.close,
            volume=price.volume)

        self.sql_client.insert("daily_price", row)

    def get_price(self, symbol: str, date: str) -> StockPrice:
        rows = self.sql_client.select("select * " +
                                      "from daily_price " +
                                      f"where symbol = '{symbol}' " +
                                      f"and date = '{date}'",
                                      self.price_mapper)

        return rows

    def price_mapper(self, row):
        return StockPrice(
            symbol=row["symbol"],
            date=row["date"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"]
        )


@dataclass
class BalanceSheetRow:
    symbol: str
    date: datetime.date
    total_assets: float
    total_liabilities: float


@dataclass
class IncomeStatementRow:
    symbol: str
    date: datetime.date
    net_income: float
    waso: int


@dataclass
class AnalysisRow:
    symbol: str
    date: datetime.date
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


@dataclass
class PriceRow:
    symbol: str
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: float
