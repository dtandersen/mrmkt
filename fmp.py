from balance_sheet import BalanceSheet
from financial import FinancialGateway
from income_statement import IncomeStatement
import requests


class FMPFinancialGateway(FinancialGateway):
    balances = {}
    incomes = {}

    def getBalanceSheet(self, symbol) -> BalanceSheet:
        json = requests.get('https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/AAPL').json()
        financials = json['financials'][0]
        return BalanceSheet(
            symbol=symbol,
            totalAssets=float(financials['Total assets']),
            totalLiabilities=float(financials['Total liabilities'])
        )

    def getIncomeStatement(self, symbol) -> IncomeStatement:
        json = requests.get('https://financialmodelingprep.com/api/v3/financials/income-statement/AAPL').json()
        financials = json['financials'][0]
        return IncomeStatement(
            symbol=symbol,
            netIncome=float(financials['Net Income']),
            waso=float(financials['Weighted Average Shs Out'])
        )
