from abc import ABC
from dataclasses import dataclass

from mrmkt.repo.provider import MarketDataProvider, ReadOnlyMarketDataProvider
from mrmkt.common.sql import Duplicate


@dataclass
class FinancialLoaderRequest:
    symbol: str


class FinancialLoaderResult:
    def on_load_symbol(self, symbol: str):
        pass


class UseCase(ABC):
    result: object

    # def execute(self):
    #     pass


class FinancialLoader(UseCase):
    result: FinancialLoaderResult

    def __init__(self, source: ReadOnlyMarketDataProvider, dest: MarketDataProvider):
        self.source = source
        self.dest = dest

    def execute(self, request: FinancialLoaderRequest, result: FinancialLoaderResult):
        self.result = result
        if request.symbol is not None:
            self.load(request.symbol)
        else:
            self.load_all()

    def load(self, symbol: str):
        source = self.source
        dest = self.dest

        self.result.on_load_symbol(symbol)

        prices = source.prices.list_prices(symbol)
        dest.prices.add_prices(prices)

        income_statements = self.source.financials.list_income_statements(symbol)
        for i in income_statements:
            try:
                self.dest.financials.add_income(i)
            except Duplicate:
                pass

        balance_sheets = self.source.financials.list_balance_sheets(symbol)
        for c in balance_sheets:
            try:
                self.dest.financials.add_balance_sheet(c)
            except Duplicate:
                pass

        cash_flows = self.source.financials.list_cash_flows(symbol)
        for c in cash_flows:
            try:
                self.dest.financials.add_cash_flow(c)
            except Duplicate:
                pass

        enterprise_value = self.source.financials.list_enterprise_value(symbol)
        for e in enterprise_value:
            try:
                self.dest.financials.add_enterprise_value(e)
            except Duplicate:
                pass

    def load_all(self):
        for symbol in self.source.tickers.get_symbols():
            self.load(symbol)
