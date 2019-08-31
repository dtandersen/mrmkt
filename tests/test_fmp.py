import unittest
from pathlib import Path
import requests_mock

from entity.balance_sheet import BalanceSheet
from entity.stock_price import StockPrice
from ext.fmp import FMPFinancialGateway, FmpApi
from entity.income_statement import IncomeStatement


class TestFMPFinancialGateway(unittest.TestCase):
    @requests_mock.Mocker()
    def test_multiple_balance_sheets(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/AAPL?period=annual',
                       text=Path('fmp/aapl-balance-sheet.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        resp = fmp.balance_sheet('AAPL')
        self.assertEqual(vars(resp[0]), vars(BalanceSheet(
            symbol='AAPL',
            date='2018-09-29',
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )))
        self.assertEqual(2, len(resp))

    @requests_mock.Mocker()
    def test_nvda_balance_sheet(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/NVDA?period=annual',
                       text=Path('fmp/NVDA-balance-sheet.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        resp = fmp.balance_sheet('NVDA')
        self.assertEqual(resp[0].symbol, 'NVDA')
        self.assertEqual(resp[0].date, '2019-01-27')
        self.assertEqual(resp[0].totalLiabilities, 3950000000.0)
        self.assertEqual(resp[0].totalAssets, 13292000000.0)

    @requests_mock.Mocker()
    def test_spy_has_no_balance_sheet(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/SPY?period=annual',
                       text="{}")
        fmp = FMPFinancialGateway(FmpApi())
        resp = fmp.balance_sheet('SPY')
        self.assertEqual(resp, [])

    @requests_mock.Mocker()
    def test_multiple_income_sheets(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/AAPL?period=annual',
                       text=Path('fmp/aapl-income.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        resp = fmp.income_statement('AAPL')
        self.assertEqual(vars(resp[0]),
                         vars(IncomeStatement(
                             symbol='AAPL',
                             date='2018-09-29',
                             waso=5000109000.0,
                             netIncome=59531000000.0
                         ))
                         )
        self.assertEqual(vars(resp[1]),
                         vars(IncomeStatement(
                             symbol='AAPL',
                             date='2017-09-30',
                             waso=5251692000.0,
                             netIncome=48351000000.0
                         )
                         ))
        self.assertEqual(2, len(resp))

    @requests_mock.Mocker()
    def test_nvda_income_statement(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/NVDA?period=annual',
                       text=Path('fmp/NVDA-income-statement.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        resp = fmp.income_statement('NVDA')
        self.assertEqual(resp[0].symbol, 'NVDA')
        self.assertEqual(resp[0].date, '2019-01-27')
        self.assertEqual(resp[0].waso, 625000000.0)
        self.assertEqual(resp[0].netIncome, 4141000000.0)

    @requests_mock.Mocker()
    def test_spy_has_no_income_statement(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/SPY?period=annual',
                       text="{}")
        fmp = FMPFinancialGateway(FmpApi())
        resp = fmp.income_statement('SPY')
        self.assertEqual(resp, [])

    @requests_mock.Mocker()
    def test_cmcsa_has_no_waso_dil(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/financials/income-statement/CMCSA?period=annual',
                       text=Path('fmp/CMCSA-income-statement.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        resp = fmp.income_statement('CMCSA')
        self.assertEqual(resp[0].symbol, 'CMCSA')
        self.assertEqual(resp[0].date, '2018-12-31')
        self.assertEqual(resp[0].waso, 4549504769.0)
        self.assertEqual(resp[0].netIncome, 11731000000.0)

    @requests_mock.Mocker()
    def test_kmi_has_no_waso(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/KMI?period=annual',
                       text=Path('fmp/KMI-income-statement.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        resp = fmp.income_statement('KMI')
        self.assertEqual(resp[0].symbol, 'KMI')
        self.assertEqual(resp[0].date, '2009-12-31')
        self.assertEqual(resp[0].waso, 0)
        self.assertEqual(resp[0].netIncome, 495000000.0)

    @requests_mock.Mocker()
    def test_price(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/AAPL',
                       text=Path('fmp/AAPL-historical.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        price = fmp.closing_price('AAPL', '2018-09-29')
        self.assertEqual(price, 223.1351)

    @requests_mock.Mocker()
    def test_price2(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/NVDA',
                       text=Path('fmp/NVDA-historical.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        price = fmp.closing_price('NVDA', '2014-06-16')
        self.assertEqual(price, 18.6516)

    @requests_mock.Mocker()
    def test_get_stocks(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/company/stock/list',
                       text=Path('fmp/symbols.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        symbols = fmp.get_stocks()
        self.assertEqual(symbols, ['SPY', 'CMCSA'])

    @requests_mock.Mocker()
    def test_get_historical_price(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/NVDA',
                       text=Path('fmp/NVDA-historical-price-full.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        price = fmp.get_daily_prices('NVDA')
        self.assertEqual(vars(price[0]), vars(StockPrice(
            symbol="NVDA",
            date="2014-06-13",
            open=18.8814,
            high=18.891,
            low=18.5272,
            close=18.7091,
            volume=5696281.0
        )))

    @requests_mock.Mocker()
    def test_get_historical_price2(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/AAPL',
                       text=Path('fmp/AAPL-historical-price-full.json').read_text())
        fmp = FMPFinancialGateway(FmpApi())
        price = fmp.get_daily_prices('AAPL')
        self.assertEqual(vars(price[0]), vars(StockPrice(
            symbol="AAPL",
            date="2014-06-13",
            open=84.5035,
            high=84.7235,
            low=83.2937,
            close=83.6603,
            volume=5.452528E7
        )))
        self.assertEqual(vars(price[1]), vars(StockPrice(
            symbol="AAPL",
            date="2014-06-16",
            open=83.8711,
            high=85.0076,
            low=83.8161,
            close=84.5035,
            volume=3.556127E7
        )))
