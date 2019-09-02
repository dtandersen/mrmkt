import datetime
from abc import abstractmethod
from typing import List, Optional

from entity.balance_sheet import BalanceSheet
from entity.income_statement import IncomeStatement
from entity.stock_price import StockPrice
from tests.test_sqlfinrepo import to_date


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


class TestFinancialGateway(InMemoryFinancialGateway):
    def add_google_financials(self):
        self.stocks.append('GOOG')
        self.addIncome(IncomeStatement(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            netIncome=30736000000.0,
            waso=750000000
        ))

        self.addBalanceSheet(BalanceSheet(
            symbol='GOOG',
            date=datetime.date(2018, 12, 1),
            totalAssets=232792000000.0,
            totalLiabilities=1264000000.0
        ))
        self.add_price(StockPrice(
            symbol='GOOG',
            date=datetime.date(2018, 11, 30),
            open=1089.07,
            high=1095.57,
            low=1077.88,
            close=1094.43,
            volume=2580612.0
        ))
        self.add_price(StockPrice(
            symbol='GOOG',
            date=datetime.date(2018, 12, 3),
            open=1103.12,
            high=1104.42,
            low=1049.98,
            close=1050.82,
            volume=2345166.0
        ))

    def add_nvidia_financials(self):
        self.stocks.append('NVDA')
        self.addIncome(IncomeStatement(
            symbol='NVDA',
            date=datetime.date(2019, 1, 27),
            netIncome=4141000000.0,
            waso=625000000
        ))

        self.addBalanceSheet(BalanceSheet(
            symbol='NVDA',
            date=datetime.date(2019, 1, 27),
            totalAssets=13292000000.0,
            totalLiabilities=3950000000.0
        ))

        self.add_price(StockPrice(
            symbol='NVDA',
            date=datetime.date(2019, 1, 28),
            open=136.2538,
            high=141.3328,
            low=130.7159,
            close=137.7107,
            volume=6.2788169E7
        ))

        self.add_price(StockPrice(
            symbol='NVDA',
            date=datetime.date(2014, 6, 13),
            open=18.8814,
            high=18.891,
            low=18.5272,
            close=18.7091,
            volume=5696281.0
        ))

    def add_apple_financials(self):
        self.stocks.append('AAPL')
        self.addIncome(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            netIncome=59531000000.0,
            waso=5000109000
        ))

        self.addBalanceSheet(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2018, 9, 29),
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        ))

        self.addIncome(IncomeStatement(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            netIncome=48351000000.0,
            waso=5251692000
        ))

        self.addBalanceSheet(BalanceSheet(
            symbol='AAPL',
            date=datetime.date(2017, 9, 30),
            totalAssets=375319000000.0,
            totalLiabilities=241272000000.0
        ))

        self.add_price(StockPrice(
            symbol='AAPL',
            date=datetime.date(2018, 10, 1),
            open=225.3196,
            high=226.7726,
            low=223.738,
            close=224.6375,
            volume=2.3600802E7
        ))

        self.add_price(StockPrice(
            symbol='AAPL',
            date=datetime.date(2017, 10, 2),
            open=150.2087,
            high=150.3937,
            low=148.7091,
            close=149.7705,
            volume=1.8698842E7
        ))

    def addSpyFinancials(self):
        self.stocks.append('SPY')

    def add_netflix_financials(self):
        self.stocks.append('NFLX')
        self.addIncome(IncomeStatement(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            netIncome=1211242000.0,
            waso=451244000
        ))

        self.addBalanceSheet(BalanceSheet(
            symbol='NFLX',
            date=datetime.date(2018, 12, 31),
            totalAssets=25974400000.0,
            totalLiabilities=20735635000.0
        ))
        self.add_price(StockPrice(
            symbol='NFLX',
            date=to_date('2018-12-31'),
            open=260.16,
            high=270.1001,
            low=260.0,
            close=267.66,
            volume=1.350892E7
        ))
        self.add_price(StockPrice(
            symbol='NFLX',
            date=to_date('2019-01-02'),
            open=259.28,
            high=269.7499,
            low=256.58,
            close=267.66,
            volume=1.1679528E7
        ))
