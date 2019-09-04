import datetime
from abc import abstractmethod
from typing import List

from common.fingate import ReadOnlyFinancialRepository
from common.sql import Duplicate
from entity.analysis import Analysis
from entity.balance_sheet import BalanceSheet
from entity.income_statement import IncomeStatement
from entity.stock_price import StockPrice


class FinancialRepository(ReadOnlyFinancialRepository):
    # @abstractmethod
    # def get_income_statements(self, symbol: str) -> List[IncomeStatement]:
    #     raise NotImplementedError

    # @abstractmethod
    # def get_income_statement(self, symbol: str, date: str) -> IncomeStatement:
    #     raise NotImplementedError

    @abstractmethod
    def add_income(self, income_statement: IncomeStatement) -> None:
        raise NotImplementedError

    # @abstractmethod
    # def get_balance_sheets(self, symbol: str) -> List[BalanceSheet]:
    #     raise NotImplementedError

    # @abstractmethod
    # def get_balance_sheet(self, symbol: str, date: str) -> BalanceSheet:
    #     raise NotImplementedError

    @abstractmethod
    def add_balance_sheet(self, balance_sheet: BalanceSheet) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_analysis(self, analysis: Analysis):
        raise NotImplementedError

    # @abstractmethod
    # def get_price(self, symbol: str, date: str) -> StockPrice:
    #     raise NotImplementedError

    @abstractmethod
    def add_price(self, price: StockPrice):
        raise NotImplementedError

    @abstractmethod
    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        raise NotImplementedError

    @abstractmethod
    def delete_analysis(self, symbol: str, date: datetime.date):
        raise NotImplementedError


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
        if self.key(analysis.symbol, analysis.date) in self.analysis:
            raise Duplicate("dup analysis")

        self.analysis[self.key(analysis.symbol, analysis.date)] = analysis

    def delete_analysis(self, symbol: str, date: datetime.date):
        try:
            self.analysis.pop(self.key(symbol, date))
        except KeyError:
            pass

    def key(self, symbol: str, date: datetime.date) -> str:
        d = date.strftime("%Y-%m-%d")
        return f"{symbol}-{d}"

    def get_price(self, symbol, date: datetime.date):
        return self.prices[self.key(symbol, date)]

    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        dates = [price.date for price in self.prices.values() if price.symbol == symbol and price.date >= date]
        d2 = dates[0]
        return self.prices[self.key(symbol, d2)]

    def add_price(self, price: StockPrice):
        if self.key(price.symbol, price.date) in self.prices:
            raise Duplicate("Duplicate: " + self.key(price.symbol, price.date))

        self.prices[self.key(price.symbol, price.date)] = price
