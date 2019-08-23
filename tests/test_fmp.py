import unittest
from pathlib import Path
import requests_mock
from fmp import FMPFinancialGateway, DefaultFmpApi


class TestStringMethods(unittest.TestCase):
    @requests_mock.Mocker()
    def test_get(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/AAPL?period=annual', text=Path('fmp/aapl-balance-sheet.json').read_text())
        fmp = FMPFinancialGateway(DefaultFmpApi())
        resp = fmp.balance_sheet('AAPL')
        self.assertEqual(resp.symbol, 'AAPL')
        self.assertEqual(resp.date, '2018-09-29')
        self.assertEqual(resp.totalLiabilities, 258578000000.0)
        self.assertEqual(resp.totalAssets, 365725000000.0)

    @requests_mock.Mocker()
    def test_nvda_balance_sheet(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/NVDA?period=annual', text=Path('fmp/NVDA-balance-sheet.json').read_text())
        fmp = FMPFinancialGateway(DefaultFmpApi())
        resp = fmp.balance_sheet('NVDA')
        self.assertEqual(resp.symbol, 'NVDA')
        self.assertEqual(resp.date, '2019-01-27')
        self.assertEqual(resp.totalLiabilities, 3950000000.0)
        self.assertEqual(resp.totalAssets, 13292000000.0)

    @requests_mock.Mocker()
    def test_spy_has_no_balance_sheet(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/SPY?period=annual', text="{}")
        fmp = FMPFinancialGateway(DefaultFmpApi())
        resp = fmp.balance_sheet('SPY')
        self.assertEqual(resp, None)

    @requests_mock.Mocker()
    def test_income(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/AAPL?period=annual', text=Path('fmp/aapl-income.json').read_text())
        fmp = FMPFinancialGateway(DefaultFmpApi())
        resp = fmp.income_statement('AAPL')
        self.assertEqual(resp.symbol, 'AAPL')
        self.assertEqual(resp.date, '2018-09-29')
        self.assertEqual(resp.waso, 5000109000.0)
        self.assertEqual(resp.netIncome, 59531000000.0)

    @requests_mock.Mocker()
    def test_nvda_income_statement(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/NVDA?period=annual', text=Path('fmp/NVDA-income-statement.json').read_text())
        fmp = FMPFinancialGateway(DefaultFmpApi())
        resp = fmp.income_statement('NVDA')
        self.assertEqual(resp.symbol, 'NVDA')
        self.assertEqual(resp.date, '2019-01-27')
        self.assertEqual(resp.waso, 625000000.0)
        self.assertEqual(resp.netIncome, 4141000000.0)

    @requests_mock.Mocker()
    def test_spy_has_no_income_statement(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/SPY?period=annual', text="{}")
        fmp = FMPFinancialGateway(DefaultFmpApi())
        resp = fmp.income_statement('SPY')
        self.assertEqual(resp, None)

    @requests_mock.Mocker()
    def test_cmcsa_has_no_waso_dil(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/CMCSA?period=annual',  text=Path('fmp/CMCSA-income-statement.json').read_text())
        fmp = FMPFinancialGateway(DefaultFmpApi())
        resp = fmp.income_statement('CMCSA')
        self.assertEqual(resp.symbol, 'CMCSA')
        self.assertEqual(resp.date, '2018-12-31')
        self.assertEqual(resp.waso, 4549504769.0)
        self.assertEqual(resp.netIncome, 11731000000.0)

    @requests_mock.Mocker()
    def test_price(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/AAPL?serietype=line', text=Path('fmp/AAPL-historical.json').read_text())
        fmp = FMPFinancialGateway(DefaultFmpApi())
        price = fmp.closing_price('AAPL', '2018-09-29')
        self.assertEqual(price, 223.1351)

    @requests_mock.Mocker()
    def test_price2(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/NVDA?serietype=line', text=Path('fmp/NVDA-historical.json').read_text())
        fmp = FMPFinancialGateway(DefaultFmpApi())
        price = fmp.closing_price('NVDA', '2014-06-16')
        self.assertEqual(price, 18.6516)

    @requests_mock.Mocker()
    def test_get_stocks(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/company/stock/list', text=Path('fmp/symbols.json').read_text())
        fmp = FMPFinancialGateway(DefaultFmpApi())
        symbols = fmp.get_stocks()
        self.assertEqual(symbols, ['SPY', 'CMCSA'])
