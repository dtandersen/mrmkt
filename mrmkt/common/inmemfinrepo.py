import datetime
from dataclasses import dataclass
from typing import List

from mrmkt.common.table import Table
from mrmkt.entity.analysis import Analysis
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.repo.financials import FinancialRepository
from mrmkt.repo.prices import PriceRepository
from mrmkt.repo.tickers import ReadOnlyTickerRepository


@dataclass
class InMemoryFinancialRepository(FinancialRepository, PriceRepository, ReadOnlyTickerRepository):
    incomes: Table
    balances: Table
    analysis: Table
    cashflows: Table
    enterprises: Table
    prices: Table
    stocks: Table

    def __init__(self):
        self.incomes = Table(symbol_date_key)
        self.balances = Table(symbol_date_key)
        self.analysis = Table(symbol_date_key)
        self.prices = Table(symbol_date_key)
        self.cashflows = Table(symbol_date_key)
        self.enterprises = Table(symbol_date_key)
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

    def get_cash_flow(self, symbol: str, date: datetime.date) -> CashFlow:
        return self.cashflows.get(f"{symbol}-{date}")

    def list_cash_flows(self, symbol: str) -> List[CashFlow]:
        return self.cashflows.filter(lambda i: i.symbol == symbol)

    def add_cash_flow(self, cash_flow: CashFlow):
        self.cashflows.add(cash_flow)

    def get_enterprise_value(self, symbol: str, date: datetime.date) -> EnterpriseValue:
        return self.enterprises.get(f"{symbol}-{date}")

    def list_enterprise_value(self, symbol: str) -> List[EnterpriseValue]:
        return self.enterprises.filter(lambda i: i.symbol == symbol)

    def add_enterprise_value(self, enterprise_value: EnterpriseValue):
        self.enterprises.add(enterprise_value)

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

    def list_prices(self, ticker: str, start: datetime.date = None, end: datetime.date = None) -> List[StockPrice]:
        prices = self.prices.filter(lambda p: p.symbol == ticker)

        if start is not None:
            prices = list(filter(lambda p: p.date >= start, prices))

        if end is not None:
            prices = list(filter(lambda p: p.date <= end, prices))

        return prices

    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        dates = [price.date for price in self.prices.filter(lambda p: p.symbol == symbol and p.date >= date)]
        earliest_date = dates[0]
        return self.prices.get(self.key(symbol, earliest_date))

    def add_price(self, price: StockPrice):
        self.prices.add(price)

    def get_symbols(self) -> List[str]:
        return list(self.stocks.all())

    def all_prices(self):
        return self.prices.all()


def symbol_date_key(obj) -> str:
    date = obj.date
    symbol = obj.symbol
    d = date.strftime("%Y-%m-%d")
    return f"{symbol}-{d}"


def string_key(symbol: str) -> str:
    return symbol
