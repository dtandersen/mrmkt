import datetime
from abc import abstractmethod
from typing import List, Optional

from entity.balance_sheet import BalanceSheet
from entity.cash_flow import CashFlow
from entity.enterprise_value import EnterpriseValue
from entity.income_statement import IncomeStatement
from entity.stock_price import StockPrice


class FinancialGateway:
    @abstractmethod
    def balance_sheet(self, symbol) -> List[BalanceSheet]:
        raise NotImplementedError

    @abstractmethod
    def income_statement(self, symbol) -> List[IncomeStatement]:
        raise NotImplementedError

    @abstractmethod
    def closing_price(self, symbol, date) -> Optional[IncomeStatement]:
        raise NotImplementedError

    @abstractmethod
    def get_stocks(self) -> Optional[List[str]]:
        raise NotImplementedError

    @abstractmethod
    def get_daily_prices(self, symbol: str) -> List[StockPrice]:
        raise NotImplementedError

    @abstractmethod
    def get_cash_flow(self, symbol: str) -> List[CashFlow]:
        raise NotImplementedError

    @abstractmethod
    def get_enterprise_value(self, symbol: str) -> List[EnterpriseValue]:
        raise NotImplementedError


class InMemoryFinancialGateway(FinancialGateway):
    balances: dict
    incomes: dict
    close: dict
    stocks: List[str]
    prices: dict

    def __init__(self):
        self.clear()

    def addBalanceSheet(self, balance_sheet: BalanceSheet):
        self.balances[f"{balance_sheet.symbol}-{balance_sheet.date}"] = balance_sheet

    def balance_sheet(self, symbol: str) -> List[BalanceSheet]:
        return list(filter(lambda b: b.symbol == symbol, self.balances.values()))

    def closing_price(self, symbol, date) -> Optional[float]:
        return self.close[f'{symbol}-{date}']

    def addIncome(self, income_statement: IncomeStatement):
        self.incomes[f"{income_statement.symbol}-{income_statement.date}"] = income_statement

    def income_statement(self, symbol: str) -> List[IncomeStatement]:
        return list(filter(lambda i: i.symbol == symbol, self.incomes.values()))

    def add_close_price(self, symbol, date, close_price):
        self.close[f'{symbol}-{date}'] = close_price

    def get_stocks(self) -> Optional[List[str]]:
        return self.stocks

    def delete_symbols(self, symbols: List[str]):
        for symbol in symbols:
            try:
                self.stocks.remove(symbol)
            except ValueError:
                pass

    def keep_symbols(self, symbols: List[str]):
        self.stocks = list(symbol for symbol in self.stocks if symbol in symbols)

    def clear(self):
        self.balances = dict()
        self.incomes = dict()
        self.close = dict()
        self.stocks = []
        self.prices = dict()

    def get_daily_prices(self, symbol: str) -> List[StockPrice]:
        return [price for price in self.prices.values() if price.symbol == symbol]

    def add_price(self, price: StockPrice):
        self.prices[self.key(price.symbol, price.date)] = price

    def key(self, symbol: str, date: datetime.date):
        d = date.strftime("%Y-%m-%d")
        return f"{symbol}-{d}"


