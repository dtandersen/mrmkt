from datetime import datetime, timedelta
from balance_sheet import BalanceSheet
from financial import FinancialGateway
from income_statement import IncomeStatement
import requests


class FMPFinancialGateway(FinancialGateway):
    def balance_sheet(self, symbol) -> BalanceSheet:
        json = requests.get(f'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/{symbol}').json()
        financials = json['financials'][0]
        return BalanceSheet(
            symbol=symbol,
            date=financials['date'],
            totalAssets=float(financials['Total assets']),
            totalLiabilities=float(financials['Total liabilities'])
        )

    def income_statement(self, symbol) -> IncomeStatement:
        json = requests.get(f'https://financialmodelingprep.com/api/v3/financials/income-statement/{symbol}').json()
        financials = json['financials'][0]
        return IncomeStatement(
            symbol=symbol,
            date=financials['date'],
            netIncome=float(financials['Net Income']),
            waso=float(financials['Weighted Average Shs Out (Dil)'])
        )

    def closing_price(self, symbol, date):
        json = requests.get(f'https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?serietype=line').json()
        # print(date)
        # print(json)
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

    @staticmethod
    def find(prices, date):
        return next((x for x in prices if x['date'] == date), None)
