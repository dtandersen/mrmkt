import logging
from datetime import datetime, timedelta
from typing import Optional, List

from entity.balance_sheet import BalanceSheet
from common.fingate import FinancialGateway
from entity.cash_flow import CashFlow
from entity.enterprise_value import EnterpriseValue
from entity.income_statement import IncomeStatement
import requests

from entity.stock_price import StockPrice
from tests.test_sqlfinrepo import to_date


class FmpApi:
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

    def get_enterprise_value(self, symbol, period='annual'):
        json = requests \
            .get(f'{self.endpoint}/enterprise-value/{symbol}?period={period}') \
            .json()
        logging.debug(json)
        return json

    def get_historical_price_full(self, symbol):
        json = requests \
            .get(f'{self.endpoint}/historical-price-full/{symbol}') \
            .json()
        logging.debug(json)
        return json

    def get_stocks(self):
        json = requests \
            .get(f'{self.endpoint}/company/stock/list') \
            .json()
        logging.debug(json)
        return json

    def get_cash_flow(self, symbol: str):
        json = requests \
            .get(f'{self.endpoint}/financials/cash-flow-statement/{symbol}') \
            .json()
        logging.debug(json)
        return json


class FMPFinancialGateway(FinancialGateway):
    def __init__(self, fmp_api: FmpApi):
        self.fmp_api = fmp_api

    def balance_sheet(self, symbol) -> List[BalanceSheet]:
        json = self.fmp_api.get_balance_sheet_statement(symbol)
        if 'financials' not in json:
            return []

        return list(map(lambda b: self.cnvt_balance(symbol, b), json['financials']))

    def cnvt_balance(self, symbol: str, balance_sheet_json) -> BalanceSheet:
        return BalanceSheet(
            symbol=symbol,
            date=to_date(balance_sheet_json['date']),
            totalAssets=float(balance_sheet_json['Total assets']),
            totalLiabilities=float(balance_sheet_json['Total liabilities']))

    def income_statement(self, symbol) -> List[IncomeStatement]:
        json = self.fmp_api.get_income_statement(symbol)
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
            waso=waso2
        )

    def closing_price(self, symbol, date) -> Optional[float]:
        json = self.fmp_api.get_historical_price_full(symbol)
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

    def get_stocks(self) -> Optional[List[str]]:
        json = self.fmp_api.get_stocks()
        return list(map(lambda row: row['symbol'], json['symbolsList']))

    @staticmethod
    def find(prices, date):
        return next((x for x in prices if x['date'] == date), None)

    def get_daily_prices(self, symbol: str) -> List[StockPrice]:
        json = self.fmp_api.get_historical_price_full(symbol)
        return [FMPFinancialGateway.map_price(row, symbol) for row in json["historical"]]

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

    def get_cash_flow(self, symbol: str) -> List[CashFlow]:
        json = self.fmp_api.get_cash_flow(symbol)
        return [FMPFinancialGateway.map_cash_flow(row, symbol) for row in json["financials"]]

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

    def get_enterprise_value(self, symbol: str) -> List[EnterpriseValue]:
        json = self.fmp_api.get_enterprise_value(symbol)
        return [FMPFinancialGateway.map_enterprise_value(row, symbol) for row in json["enterpriseValues"]]

    @staticmethod
    def map_enterprise_value(json, symbol: str) -> EnterpriseValue:
        return EnterpriseValue(
            symbol=symbol,
            date=to_date(json["date"]),
            stock_price=float(json["Stock Price"]),
            shares_outstanding=float(json["Number of Shares"]),
            market_cap=float(json["Market Capitalization"])
        )
