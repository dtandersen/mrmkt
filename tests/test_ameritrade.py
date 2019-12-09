import unittest
from datetime import datetime, timezone
from pathlib import Path

import requests_mock
from hamcrest import *

from mrmkt.common.util import to_datetime_utc
from mrmkt.ext.tdameritrade import TDAmeritradeClient, Candle, TokenGenerator


class MockTokenGenerator(TokenGenerator):
    def __init__(self):
        super().__init__(None, None, None, None)

    def authenticate(self):
        self._access_code = 1234
        return {"access_token": 1234}


class TestTDAmeritradeClient(unittest.TestCase):
    @requests_mock.Mocker()
    def test_list_prices(self, m):
        m.register_uri('GET',
                       'https://api.tdameritrade.com/v1/marketdata/SPY/pricehistory',
                       request_headers={
                           "Authorization": "Bearer 1234"
                       },
                       text=Path('tdameritrade/SPY-history.json').read_text())
        client = TDAmeritradeClient(MockTokenGenerator())
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
