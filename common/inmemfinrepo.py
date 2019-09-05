import datetime
from dataclasses import dataclass
from typing import List

from common.onion import FinancialRepository
from common.table import Table
from entity.analysis import Analysis
from entity.balance_sheet import BalanceSheet
from entity.cash_flow import CashFlow
from entity.enterprise_value import EnterpriseValue
from entity.income_statement import IncomeStatement
from entity.stock_price import StockPrice


@dataclass
class InMemoryFinancialRepository(FinancialRepository):
    incomes: Table
    balances: Table
    analysis: Table
    cashflows: Table
    prices: Table
    stocks: Table

    def __init__(self):
        self.incomes = Table(symbol_date_key)
        self.balances = Table(symbol_date_key)
        self.analysis = Table(symbol_date_key)
        self.prices = Table(symbol_date_key)
        self.cashflows = Table(symbol_date_key)
        self.stocks = Table(string_key)

    def get_income_statement(self, symbol: str, date: datetime.date) -> IncomeStatement:
        return self.incomes.get(self.key(symbol, date))

    def list_income_statements(self, symbol: str) -> List[IncomeStatement]:
        return self.incomes.filter(lambda i: i.symbol == symbol)

    def add_income(self, income_statement: IncomeStatement) -> None:
        self.incomes.add(income_statement)

    def get_balance_sheet(self, symbol: str, date: str) -> BalanceSheet:
        return self.balances.get(f"{symbol}-{date}")

    def list_balance_sheets(self, symbol: str) -> List[BalanceSheet]:
        return self.balances.filter(lambda i: i.symbol == symbol)

    def add_balance_sheet(self, balance_sheet: BalanceSheet) -> None:
        self.balances.add(balance_sheet)

    def get_enterprise_value(self, symbol: str) -> List[EnterpriseValue]:
        pass

    def list_cash_flows(self, symbol: str) -> List[CashFlow]:
        pass

    def add_cash_flow(self, cash_flow: CashFlow):
        self.cashflows.add(cash_flow)

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
        return self.analysis.filter(lambda s: s.symbol == symbol)

    def add_analysis(self, analysis: Analysis):
        self.analysis.add(analysis)

    def delete_analysis(self, symbol: str, date: datetime.date):
        self.analysis.pop(self.key(symbol, date))

    def key(self, symbol: str, date: datetime.date) -> str:
        d = date.strftime("%Y-%m-%d")
        return f"{symbol}-{d}"

    def get_price(self, symbol, date: datetime.date):
        return self.prices.get(self.key(symbol, date))

    def list_prices(self, symbol: str) -> List[StockPrice]:
        return self.prices.filter(lambda p: p.symbol == symbol)

    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        dates = [price.date for price in self.prices.filter(lambda p: p.symbol == symbol and p.date >= date)]
        earliest_date = dates[0]
        return self.prices.get(self.key(symbol, earliest_date))

    def add_price(self, price: StockPrice):
        self.prices.add(price)

    def get_symbols(self) -> List[str]:
        return list(self.stocks.all())

    def get_cash_flow(self, symbol: str, date: datetime.date) -> CashFlow:
        return self.cashflows.get(f"{symbol}-{date}")


def symbol_date_key(obj) -> str:
    date = obj.date
    symbol = obj.symbol
    d = date.strftime("%Y-%m-%d")
    return f"{symbol}-{d}"


def string_key(symbol: str) -> str:
    return symbol
