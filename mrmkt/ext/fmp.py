import logging
from datetime import datetime, timedelta
from typing import Optional, List

import requests

from mrmkt.common.util import to_date
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.repo.financials import ReadOnlyFinancialRepository
from mrmkt.repo.prices import ReadOnlyPriceRepository
from mrmkt.repo.tickers import ReadOnlyTickerRepository


class FmpClient:
    endpoint: str = "https://financialmodelingprep.com/api/v3"

    def get_balance_sheet_statement(self, symbol, period='annual'):
        json = requests \
            .get(f'{self.endpoint}/financials/balance-sheet-statement/{symbol}?period={period}') \
            .json()
        logging.debug(json)
        return json

    def get_income_statement(self, symbol, period='annual'):
        json = requests \
            .get(f'{self.endpoint}/financials/income-statement/{symbol}?period={period}') \
            .json()
        logging.debug(json)
        return json

    def get_cash_flow(self, symbol: str, period='annual'):
        json = requests \
            .get(f'{self.endpoint}/financials/cash-flow-statement/{symbol}?period={period}') \
            .json()
        logging.debug(json)
        return json

    def get_enterprise_value(self, symbol, period='annual'):
        json = requests \
            .get(f'{self.endpoint}/enterprise-value/{symbol}?period={period}') \
            .json()
        logging.debug(json)
        return json

    def get_historical_price_full(self, symbol: str, start: datetime.date = None):
        if start is not None:
            xdate = start.strftime("%Y-%m-%d")
            y = f"from={xdate}"
        else:
            y = ""

        json = requests \
            .get(f'{self.endpoint}/historical-price-full/{symbol}?{y}') \
            .json()
        logging.debug(json)
        return json

    def get_stocks(self):
        json = requests \
            .get(f'{self.endpoint}/company/stock/list') \
            .json()
        logging.debug(json)
        return json


class FMPReadOnlyFinancialRepository(ReadOnlyFinancialRepository, ReadOnlyPriceRepository, ReadOnlyTickerRepository):
    def __init__(self, client: FmpClient):
        self.client = client

    def list_balance_sheets(self, symbol) -> List[BalanceSheet]:
        json = self.client.get_balance_sheet_statement(symbol)
        if 'financials' not in json:
            return []

        return list(map(lambda b: self.cnvt_balance(symbol, b), json['financials']))

    def cnvt_balance(self, symbol: str, balance_sheet_json) -> BalanceSheet:
        return BalanceSheet(
            symbol=symbol,
            date=to_date(balance_sheet_json['date']),
            totalAssets=float(balance_sheet_json['Total assets']),
            totalLiabilities=float(balance_sheet_json['Total liabilities']))

    def list_income_statements(self, symbol) -> List[IncomeStatement]:
        json = self.client.get_income_statement(symbol)
        if 'financials' not in json:
            return []

        return list(map(lambda i: self.cnvt_income(symbol, i), json['financials']))

    def cnvt_income(self, symbol: str, income_stmt_json) -> IncomeStatement:
        if 'Weighted Average Shs Out (Dil)' in income_stmt_json \
                and income_stmt_json['Weighted Average Shs Out (Dil)'] is not "":
            waso2 = float(income_stmt_json['Weighted Average Shs Out (Dil)'])
        elif 'Weighted Average Shs Out' in income_stmt_json and income_stmt_json['Weighted Average Shs Out'] is not "":
            waso2 = float(income_stmt_json['Weighted Average Shs Out'])
        else:
            waso2 = 0

        return IncomeStatement(
            symbol=symbol,
            date=to_date(income_stmt_json['date']),
            netIncome=float(income_stmt_json['Net Income']),
            waso=waso2,
            consolidated_net_income=-1
        )

    def list_cash_flows(self, symbol: str) -> List[CashFlow]:
        json = self.client.get_cash_flow(symbol)
        if 'financials' not in json:
            return []

        return [FMPReadOnlyFinancialRepository.map_cash_flow(row, symbol) for row in json["financials"]]

    @staticmethod
    def map_cash_flow(json, symbol: str) -> CashFlow:
        return CashFlow(
            symbol=symbol,
            date=to_date(json["date"]),
            operating_cash_flow=float(json["Operating Cash Flow"]),
            capital_expenditure=float(json["Capital Expenditure"]),
            free_cash_flow=float(json["Free Cash Flow"]),
            dividend_payments=float(json["Dividend payments"] if json["Dividend payments"] != "" else 0)
        )

    def list_enterprise_value(self, symbol: str) -> List[EnterpriseValue]:
        json = self.client.get_enterprise_value(symbol)
        if 'enterpriseValues' not in json:
            return []
        return [FMPReadOnlyFinancialRepository.map_enterprise_value(row, symbol) for row in json["enterpriseValues"]]

    @staticmethod
    def map_enterprise_value(json, symbol: str) -> EnterpriseValue:
        try:
            shares_outstanding = float(json["Number of Shares"])
        except ValueError:
            shares_outstanding = 0

        return EnterpriseValue(
            symbol=symbol,
            date=to_date(json["date"]),
            stock_price=float(json["Stock Price"]),
            shares_outstanding=shares_outstanding,
            market_cap=float(json["Market Capitalization"])
        )

    def closing_price(self, symbol, date) -> Optional[float]:
        json = self.client.get_historical_price_full(symbol)
        dd1 = date
        dd = datetime.strptime(date, '%Y-%m-%d')
        prices = json['historical']
        price = None
        while price is None:
            price = self.find(prices, dd1)
            if price is None:
                dd = dd - timedelta(days=1.0)
                dd1 = dd.strftime('%Y-%m-%d')

        return price['close']

    def get_tickers(self) -> List[Ticker]:
        raise NotImplementedError

    def get_symbols(self) -> List[str]:
        json = self.client.get_stocks()
        return list(map(lambda row: row['symbol'], json['symbolsList']))

    @staticmethod
    def find(prices, date):
        return next((x for x in prices if x['date'] == date), None)

    def list_prices(self, symbol: str, start: datetime.date = None, end: datetime.date = None) -> List[StockPrice]:
        json = self.client.get_historical_price_full(symbol, start=start)
        prices = []
        if "historical" not in json:
            return prices

        for row in json["historical"]:
            try:
                prices.append(FMPReadOnlyFinancialRepository.map_price(row, symbol))
            except KeyError:
                # warn maybe?
                pass

        return prices

    @staticmethod
    def map_price(json, symbol: str) -> StockPrice:
        return StockPrice(
            symbol=symbol,
            date=to_date(json["date"]),
            open=json["open"],
            high=json["high"],
            low=json["low"],
            close=json["close"],
            volume=json["volume"]
        )

    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        raise NotImplementedError

    def get_income_statement(self, symbol: str, date: datetime.date) -> List[IncomeStatement]:
        raise NotImplementedError

    def get_balance_sheet(self, symbol, date: datetime.date) -> List[BalanceSheet]:
        raise NotImplementedError

    def get_cash_flow(self, symbol: str, date: datetime.date) -> CashFlow:
        raise NotImplementedError

    def get_enterprise_value(self, symbol: str, date: datetime.date) -> EnterpriseValue:
        raise NotImplementedError
