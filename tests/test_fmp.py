import unittest
from pathlib import Path
import requests_mock

from entity.balance_sheet import BalanceSheet
from entity.cash_flow import CashFlow
from entity.enterprise_value import EnterpriseValue
from entity.stock_price import StockPrice
from ext.fmp import FMPReadOnlyFinancialRepository, FmpClient
from entity.income_statement import IncomeStatement
from tests.test_sqlfinrepo import to_date
from hamcrest import *


class TestFMPFinancialGateway(unittest.TestCase):
    @requests_mock.Mocker()
    def test_multiple_balance_sheets(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/AAPL?period=annual',
                       text=Path('fmp/aapl-balance-sheet.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_balance_sheets('AAPL')
        self.assertEqual(vars(resp[0]), vars(BalanceSheet(
            symbol='AAPL',
            date=to_date('2018-09-29'),
            totalAssets=365725000000.0,
            totalLiabilities=258578000000.0
        )))
        self.assertEqual(2, len(resp))

    @requests_mock.Mocker()
    def test_nvda_balance_sheet(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/NVDA?period=annual',
                       text=Path('fmp/NVDA-balance-sheet.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_balance_sheets('NVDA')
        self.assertEqual(resp[0].symbol, 'NVDA')
        self.assertEqual(resp[0].date, to_date('2019-01-27'))
        self.assertEqual(resp[0].totalLiabilities, 3950000000.0)
        self.assertEqual(resp[0].totalAssets, 13292000000.0)

    @requests_mock.Mocker()
    def test_multiple_income_sheets(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/AAPL?period=annual',
                       text=Path('fmp/aapl-income.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_income_statements('AAPL')
        self.assertEqual(vars(resp[0]),
                         vars(IncomeStatement(
                             symbol='AAPL',
                             date=to_date('2018-09-29'),
                             waso=5000109000,
                             netIncome=59531000000.0,
                             consolidated_net_income=-1
                         ))
                         )
        self.assertEqual(vars(resp[1]),
                         vars(IncomeStatement(
                             symbol='AAPL',
                             date=to_date('2017-09-30'),
                             waso=5251692000,
                             netIncome=48351000000.0,
                             consolidated_net_income=-1
                         )
                         ))
        self.assertEqual(2, len(resp))

    @requests_mock.Mocker()
    def test_nvda_income_statement(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/NVDA?period=annual',
                       text=Path('fmp/NVDA-income-statement.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_income_statements('NVDA')
        self.assertEqual(resp[0].symbol, 'NVDA')
        self.assertEqual(resp[0].date, to_date('2019-01-27'))
        self.assertEqual(resp[0].waso, 625000000.0)
        self.assertEqual(resp[0].netIncome, 4141000000.0)

    @requests_mock.Mocker()
    def test_spy_has_no_balance_sheet(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/financials/balance-sheet-statement/SPY?period=annual',
                       text="{}")
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_balance_sheets('SPY')
        self.assertEqual(resp, [])

    @requests_mock.Mocker()
    def test_spy_has_no_income_statement(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/SPY?period=annual',
                       text="{}")
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_income_statements('SPY')
        self.assertEqual(resp, [])

    @requests_mock.Mocker()
    def test_spy_has_no_cash_flow(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/financials/cash-flow-statement/SPY?period=annual',
                       text="{}")
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_cash_flows('SPY')
        self.assertEqual(resp, [])

    @requests_mock.Mocker()
    def test_spy_has_no_enterprise_value(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/enterprise-value/SPY?period=annual',
                       text="{}")
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_enterprise_value('SPY')
        self.assertEqual(resp, [])

    @requests_mock.Mocker()
    def test_cmcsa_has_no_waso_dil(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/financials/income-statement/CMCSA?period=annual',
                       text=Path('fmp/CMCSA-income-statement.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_income_statements('CMCSA')
        self.assertEqual(resp[0].symbol, 'CMCSA')
        self.assertEqual(resp[0].date, to_date('2018-12-31'))
        self.assertEqual(resp[0].waso, 4549504769.0)
        self.assertEqual(resp[0].netIncome, 11731000000.0)

    @requests_mock.Mocker()
    def test_cmcsa_has_no_shares_outstanding(self, m):
        m.register_uri('GET',
                       'https://financialmodelingprep.com/api/v3/enterprise-value/cmcsa?period=annual',
                       text=Path('fmp/CMCSA-enterprise-value.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_enterprise_value('CMCSA')
        self.assertEqual(resp[0].shares_outstanding, 0)

    @requests_mock.Mocker()
    def test_kmi_has_no_waso(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/income-statement/KMI?period=annual',
                       text=Path('fmp/KMI-income-statement.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        resp = fmp.list_income_statements('KMI')
        self.assertEqual(resp[0].symbol, 'KMI')
        self.assertEqual(resp[0].date, to_date('2009-12-31'))
        self.assertEqual(resp[0].waso, 0)
        self.assertEqual(resp[0].netIncome, 495000000.0)

    @requests_mock.Mocker()
    def test_price(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/AAPL',
                       text=Path('fmp/AAPL-historical.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        price = fmp.closing_price('AAPL', '2018-09-29')
        self.assertEqual(price, 223.1351)

    @requests_mock.Mocker()
    def test_price2(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/NVDA',
                       text=Path('fmp/NVDA-historical.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        price = fmp.closing_price('NVDA', '2014-06-16')
        self.assertEqual(price, 18.6516)

    @requests_mock.Mocker()
    def test_get_stocks(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/company/stock/list',
                       text=Path('fmp/symbols.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        symbols = fmp.get_symbols()
        self.assertEqual(symbols, ['SPY', 'CMCSA'])

    @requests_mock.Mocker()
    def test_get_historical_price(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/NVDA?from=2019-01-01',
                       text=Path('fmp/NVDA-historical-price-full.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        price = fmp.list_prices('NVDA')
        self.assertEqual(vars(price[0]), vars(StockPrice(
            symbol="NVDA",
            date=to_date("2014-06-13"),
            open=18.8814,
            high=18.891,
            low=18.5272,
            close=18.7091,
            volume=5696281.0
        )))

    @requests_mock.Mocker()
    def test_get_historical_price2(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/AAPL?from=2019-01-01',
                       text=Path('fmp/AAPL-historical-price-full.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        price = fmp.list_prices('AAPL')
        self.assertEqual(vars(price[0]), vars(StockPrice(
            symbol="AAPL",
            date=to_date("2014-06-13"),
            open=84.5035,
            high=84.7235,
            low=83.2937,
            close=83.6603,
            volume=5.452528E7
        )))
        self.assertEqual(vars(price[1]), vars(StockPrice(
            symbol="AAPL",
            date=to_date("2014-06-16"),
            open=83.8711,
            high=85.0076,
            low=83.8161,
            close=84.5035,
            volume=3.556127E7
        )))

    @requests_mock.Mocker()
    def test_get_historical_price_no_prices(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/AAPL?from=2019-01-01',
                       text="{}")
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        prices = fmp.list_prices('AAPL')
        assert_that(prices, empty())

    @requests_mock.Mocker()
    def test_malformed_price(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/WMT?from=2019-01-01',
                       text=Path('fmp/WMT-historical-price-full.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        prices = fmp.list_prices('WMT')
        assert_that(prices, equal_to([
            StockPrice(
                symbol="WMT",
                date=to_date("2019-05-10"),
                open=0.3649,
                high=0.4093,
                low=0.3599,
                close=0.3656,
                volume=5.1037237E7
            )
        ]))

    @requests_mock.Mocker()
    def test_list_prices_from_date(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/historical-price-full/WMT?from=2019-05-10',
                       text=Path('fmp/WMT-historical-price-full.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        prices = fmp.list_prices(symbol='WMT', start=to_date("2019-05-10"))
        assert_that(prices, equal_to([
            StockPrice(
                symbol="WMT",
                date=to_date("2019-05-10"),
                open=0.3649,
                high=0.4093,
                low=0.3599,
                close=0.3656,
                volume=5.1037237E7
            )
        ]))

    @requests_mock.Mocker()
    def test_get_multiple_cash_flow(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/cash-flow-statement/AAPL',
                       text=Path('fmp/AAPL-cash-flow.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        cash_flow = fmp.list_cash_flows('AAPL')
        self.assertEqual(vars(cash_flow[0]), vars(CashFlow(
            symbol="AAPL",
            date=to_date("2018-09-29"),
            operating_cash_flow=77434000000.0,
            capital_expenditure=-13313000000.0,
            free_cash_flow=64121000000.0,
            dividend_payments=-13712000000.0
        )))
        self.assertEqual(vars(cash_flow[1]), vars(CashFlow(
            symbol="AAPL",
            date=to_date("2017-09-30"),
            operating_cash_flow=64225000000.0,
            capital_expenditure=-12451000000.0,
            free_cash_flow=51774000000.0,
            dividend_payments=-12769000000.0
        )))

    @requests_mock.Mocker()
    def test_get_single_cash_flow(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/financials/cash-flow-statement/GOOG',
                       text=Path('fmp/GOOG-cash-flow.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        cash_flow = fmp.list_cash_flows('GOOG')
        self.assertEqual(vars(cash_flow[0]), vars(CashFlow(
            symbol="GOOG",
            date=to_date("2018-12-01"),
            operating_cash_flow=47971000000.0,
            capital_expenditure=-26630000000.0,
            free_cash_flow=21341000000.0,
            dividend_payments=0
        )))

    @requests_mock.Mocker()
    def test_get_multiple_enterprise_value(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/enterprise-value/AAPL?period=annual',
                       text=Path('fmp/AAPL-enterprise-value.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        enterprise_value = fmp.list_enterprise_value('AAPL')
        self.assertEqual(vars(enterprise_value[0]), vars(EnterpriseValue(
            symbol="AAPL",
            date=to_date("2018-09-29"),
            stock_price=224.6375,
            shares_outstanding=5000109000.0,
            market_cap=1.1232119854875E12
        )))
        self.assertEqual(vars(enterprise_value[1]), vars(EnterpriseValue(
            symbol="AAPL",
            date=to_date("2017-09-30"),
            stock_price=149.7705,
            shares_outstanding=5251692000.0,
            market_cap=7.86548536686E11
        )))

    @requests_mock.Mocker()
    def test_get_single_enterprise_value(self, m):
        m.register_uri('GET', 'https://financialmodelingprep.com/api/v3/enterprise-value/GOOG?period=annual',
                       text=Path('fmp/GOOG-enterprise-value.json').read_text())
        fmp = FMPReadOnlyFinancialRepository(FmpClient())
        enterprise_value = fmp.list_enterprise_value('GOOG')
        self.assertEqual(vars(enterprise_value[0]), vars(EnterpriseValue(
            symbol="GOOG",
            date=to_date("2018-12-01"),
            stock_price=1106.43,
            shares_outstanding=750000000.0,
            market_cap=8.298225E11
        )))
