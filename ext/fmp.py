import logging
from datetime import datetime, timedelta
from typing import Optional, List

from entity.balance_sheet import BalanceSheet
from common.fingate import FinancialGateway
from entity.income_statement import IncomeStatement
import requests


# class FmpApi:
#     def get_balance_sheet_statement(self, symbol, period='annual'):
#         pass
#
#     def get_income_statement(self, symbol, period='annual'):
#         pass
#
#     def get_enterprise_value(self, symbol, period='annual'):
#         pass
#
#     def get_historical_price_full(self, symbol):
#         pass
#
#     def get_stocks(self) -> dict:
#         pass


class FmpApi:
    def get_balance_sheet_statement(self, symbol, period='annual'):
        json = requests \
            .get(f'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/{symbol}?period={period}') \
            .json()
        logging.debug(json)
        return json

    def get_income_statement(self, symbol, period='annual'):
        json = requests \
            .get(f'https://financialmodelingprep.com/api/v3/financials/income-statement/{symbol}?period={period}') \
            .json()
        logging.debug(json)
        return json

    def get_enterprise_value(self, symbol, period='annual'):
        json = requests \
            .get(f'https://financialmodelingprep.com/api/v3/enterprise-value/{symbol}?period={period}') \
            .json()
        logging.debug(json)
        return json

    def get_historical_price_full(self, symbol):
        json = requests \
            .get(f'https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?serietype=line') \
            .json()
        logging.debug(json)
        return json

    def get_stocks(self):
        json = requests \
            .get('https://financialmodelingprep.com/api/v3/company/stock/list') \
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
            date=balance_sheet_json['date'],
            totalAssets=float(balance_sheet_json['Total assets']),
            totalLiabilities=float(balance_sheet_json['Total liabilities']))

    def income_statement(self, symbol) -> List[IncomeStatement]:
        json = self.fmp_api.get_income_statement(symbol)
        if 'financials' not in json:
            return []

        return list(map(lambda i: self.cnvt_income(symbol, i), json['financials']))

    def cnvt_income(self, symbol: str, income_stmt_json) -> IncomeStatement:
        if 'Weighted Average Shs Out (Dil)' in income_stmt_json and income_stmt_json['Weighted Average Shs Out (Dil)'] is not "":
            waso2 = float(income_stmt_json['Weighted Average Shs Out (Dil)'])
        elif 'Weighted Average Shs Out' in income_stmt_json and income_stmt_json['Weighted Average Shs Out'] is not "":
            waso2 = float(income_stmt_json['Weighted Average Shs Out'])
        else:
            waso2 = 0

        return IncomeStatement(
            symbol=symbol,
            date=income_stmt_json['date'],
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
