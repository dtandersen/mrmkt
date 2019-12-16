from dataclasses import dataclass
from typing import List
from urllib import parse as up

import datetime as datetime
import mechanize
import requests


@dataclass
class Candle:
    open: float = None
    high: float = None
    low: float = None
    close: float = None
    volume: float = None
    datetime: datetime = None


@dataclass
class Position:
    symbol: str
    shares: float
    price: float


@dataclass
class Portfolio:
    equity: float
    positions: List[Position]


class TokenGenerator:
    def __init__(self, redirect, consumer_key, username, password):
        self.password = password
        self.username = username
        self.consumer_key = consumer_key
        self.redirect = redirect
        self._access_code = None

    """
    { 
      'access_token': '...', 
      'refresh_token': '...,
      'expires_in': 1800, 
      'refresh_token_expires_in': 7776000, 
      'token_type': 'Bearer'
    }
    """

    def authenticate(self):
        client_id = self.consumer_key + '@AMER.OAUTHAP'
        url = 'https://auth.tdameritrade.com/auth?response_type=code&redirect_uri=' + up.quote(
            self.redirect) + '&client_id=' + up.quote(client_id)
        # print(url)
        br = mechanize.Browser()
        br.set_handle_robots(False)
        br.open(url)
        br.select_form(nr=0)
        # print(br.form)
        br.form['su_username'] = self.username
        br.form['su_password'] = self.password
        req = br.submit(id="accept")
        # print(req.code)
        br.select_form(nr=0)
        # print(br.form)
        br.set_handle_redirect(False)
        try:
            req = br.submit(id="accept")
        except mechanize._mechanize.HTTPError as response:
            # print(response.hdrs)
            location = response.headers["Location"]
            # print(response.geturl())
            # pass
        # print(location)
        o = up.urlparse(location)
        code = up.parse_qs(o.query)['code'][0]
        # print(code)
        # return code
        resp = requests.post('https://api.tdameritrade.com/v1/oauth2/token',
                             headers={'Content-Type': 'application/x-www-form-urlencoded'},
                             data={'grant_type': 'authorization_code',
                                   'refresh_token': '',
                                   'access_type': 'offline',
                                   'code': code,
                                   'client_id': client_id,
                                   'redirect_uri': self.redirect})
        json = resp.json()
        # print(json)
        self._access_code = json["access_token"]
        return json

    def access_token(self):
        self.authenticate()
        return self._access_code


class TDAmeritradeClient:
    def __init__(self, token_generator: TokenGenerator):
        self.tokenGenerator = token_generator

    def history(self, symbol: str):
        def map_candle(candle):
            return Candle(
                open=candle["open"],
                high=candle["high"],
                low=candle["low"],
                close=candle["close"],
                volume=candle["volume"],
                datetime=datetime.datetime.fromtimestamp(candle["datetime"] / 1000, datetime.timezone.utc)
            )

        d = datetime.datetime.utcnow()
        epoch = datetime.datetime(1970, 1, 1)
        endDate = (d - epoch).total_seconds()
        startDate = endDate - (3600 * 24)
        # print(f"endData={endDate}")
        # print(f"startDate={startDate}")
        endms = int(endDate * 1000)
        startms = int(startDate * 1000)
        json = requests.get(f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory?frequencyType=minute&frequency=15&startDate={startms}&endDate={endms}", headers=self.headers()) \
            .json()
        # print(json)
        candles = [map_candle(c) for c in json["candles"]]
        return candles

    def headers(self):
        return {
            "Authorization": f"Bearer {self.tokenGenerator.access_token()}"
        }

    def list_positions(self, accountid):
        def map_portfolio(json):
            def map_position(json):
                return Position(
                    symbol=json["instrument"]["symbol"],
                    shares=json["longQuantity"],
                    price=json["averagePrice"]
                )

            securitiesAccount = json["securitiesAccount"]
            equity = securitiesAccount["currentBalances"]["equity"]
            positions = [map_position(c) for c in securitiesAccount["positions"]]

            return Portfolio(equity=equity, positions=positions)

        response = requests.get(f"https://api.tdameritrade.com/v1/accounts/{accountid}?fields=positions",
                                headers=self.headers())
        # print(response.text)
        return map_portfolio(response.json())
