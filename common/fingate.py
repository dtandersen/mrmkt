from abc import abstractmethod
from typing import List, Optional

from entity.balance_sheet import BalanceSheet
from entity.income_statement import IncomeStatement
from entity.stock_price import StockPrice


class FinancialGateway:
    @abstractmethod
    def balance_sheet(self, symbol) -> List[BalanceSheet]:
        pass

    @abstractmethod
    def income_statement(self, symbol) -> List[IncomeStatement]:
        pass

    @abstractmethod
    def closing_price(self, symbol, date) -> Optional[IncomeStatement]:
        pass

    @abstractmethod
    def get_stocks(self) -> Optional[List[str]]:
        pass

    @abstractmethod
    def get_daily_prices(self, symbol: str) -> List[StockPrice]:
        pass


class InMemoryFinancialGateway(FinancialGateway):
    balances: dict
    incomes: dict
    close: dict
    stocks: List[str]

    def __init__(self):
        self.clear()

    def addBalanceSheet(self, balance_sheet: BalanceSheet):
        self.balances[f"{balance_sheet.symbol}-{balance_sheet.date}"] = balance_sheet

    def balance_sheet(self, symbol: str) -> List[BalanceSheet]:
        return list(filter(lambda b: b.symbol == symbol, self.balances.values()))

    def closing_price(self, symbol, date) -> Optional[float]:
        return self.close[f'{symbol}-{date}']

    def addIncome(self, income_statement : IncomeStatement):
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


class TestFinancialGateway(InMemoryFinancialGateway):
    def addGoogleFinancials(self):
        self.stocks.append('GOOG')
        self.addIncome(IncomeStatement(
            symbol='GOOG',
            date='2018-12',
            netIncome=30736000000.0,
            waso=750000000.0
        ))

        self.addBalanceSheet(BalanceSheet(
            symbol='GOOG',
            date='2018-12',
            totalAssets=232792000000.0,
            totalLiabilities=1264000000.0
        ))

    def addNvidiaFinancials(self):
        self.stocks.append('NVDA')
        self.addIncome(IncomeStatement(
            symbol='NVDA',
            date='2019-01-27',
            netIncome=4141000000.0,
            waso=625000000.0
        ))

        self.addBalanceSheet(BalanceSheet(
            symbol='NVDA',
            date='2019-01-27',
            totalAssets=13292000000.0,
            totalLiabilities=3950000000.0
        ))

    def addAppleFinancials(self):
        self.stocks.append('AAPL')
        self.addIncome(IncomeStatement(
            symbol='AAPL',
            date='2018-09-29',
            netIncome=59531000000.0,
            waso=5000109000.0
        ))

        self.addBalanceSheet(BalanceSheet(
            symbol='AAPL',
            date='2018-09-29',
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        ))

        self.addIncome(IncomeStatement(
            symbol='AAPL',
            date='2017-09-30',
            netIncome=48351000000.0,
            waso=5251692000.0
        ))

        self.addBalanceSheet(BalanceSheet(
            symbol='AAPL',
            date='2017-09-30',
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        ))

    def addSpyFinancials(self):
        self.stocks.append('SPY')
