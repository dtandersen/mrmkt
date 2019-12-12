import unittest
from datetime import datetime, timezone
from pathlib import Path

import requests_mock
from hamcrest import *

from mrmkt.common.util import to_datetime_utc
from mrmkt.ext.tdameritrade import TDAmeritradeClient, Candle, TokenGenerator, Position


class MockTokenGenerator(TokenGenerator):
    def __init__(self, access_code):
        super().__init__(None, None, None, None)
        self._access_code = access_code

    def authenticate(self):
        return {"access_token": self._access_code}


class TestTDAmeritradeClient(unittest.TestCase):
    @requests_mock.Mocker()
    def test_list_prices(self, m):
        m.register_uri('GET',
                       'https://api.tdameritrade.com/v1/marketdata/SPY/pricehistory',
                       request_headers={
                           "Authorization": "Bearer 1234"
                       },
                       text=Path('tdameritrade/SPY-history.json').read_text())
        client = TDAmeritradeClient(MockTokenGenerator("1234"))
        history = client.history('SPY')
        assert_that(history, equal_to([
            Candle(
                open=310.91,
                high=311.11,
                low=310.91,
                close=311.03,
                volume=8190,
                datetime=to_datetime_utc("2019-11-22 12:00:00")
            ),
            Candle(
                open=311.05,
                high=311.09,
                low=310.96,
                close=311.01,
                volume=15366,
                datetime=to_datetime_utc("2019-11-22 12:15:00")
            )]))

    @requests_mock.Mocker()
    def test_fetch_portfolio(self, m):
        m.register_uri('GET',
                       'https://api.tdameritrade.com/v1/accounts/12345678?fields=positions',
                       request_headers={
                           "Authorization": "Bearer 2345"
                       },
                       text=Path('tdameritrade/account-12345678.json').read_text())
        client = TDAmeritradeClient(MockTokenGenerator("2345"))

        portfolio = client.list_positions('12345678')
        assert_that(portfolio.equity, equal_to(3441.67))

        positions = portfolio.positions
        assert_that(positions, equal_to([
            Position(
                symbol="ENPH",
                shares=35.0,
                price=23.901414
            ),
            Position(
                symbol="WOOD",
                shares=5.0,
                price=65.22
            )]))
