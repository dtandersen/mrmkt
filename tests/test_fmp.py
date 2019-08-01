import unittest
from pathlib import Path

import requests_mock
from balance_sheet import BalanceSheet
from fmp import FMPFinancialGateway
from income_statement import IncomeStatement


class TestStringMethods(unittest.TestCase):
    @requests_mock.Mocker()
    def test_get(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/AAPL', text=Path('aapl.json').read_text())
        fmp = FMPFinancialGateway()
        resp = fmp.getBalanceSheet('AAPL')
        self.assertEqual(resp.totalLiabilities, 258578000000.0)
        self.assertEqual(resp.totalAssets, 365725000000.0)
        self.assertEqual(resp.symbol, 'AAPL')

    @requests_mock.Mocker()
    def test_income(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/AAPL', text=Path('aapl-income.json').read_text())
        fmp = FMPFinancialGateway()
        resp = fmp.getIncomeStatement('AAPL')
        self.assertEqual(resp.symbol, 'AAPL')
        self.assertEqual(resp.waso, 4955377000.0)
        self.assertEqual(resp.netIncome, 59531000000.0)
