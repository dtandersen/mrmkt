import time
from dataclasses import dataclass

import yaml

from atradeauth import tdlogin
from tdameritrade import TDClient
from datetime import datetime


def read_config():
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
        return config


config = read_config()
ameritrade = config["ameritrade"]
redirect = ameritrade["redirect"]
consumer_key = ameritrade["consumer_key"]
username = ameritrade["username"]
password = ameritrade["password"]


@dataclass
class PriceData:
    ticker: str
    price: float
    lastPrice: float
    direction: str
    reversed: bool
    high: float
    low: float


class PriceTracker:
    def __init__(self):
        self.history = {}

    def add(self, ticker, price):
        if ticker in self.history:
            pd = self.history[ticker]
        else:
            pd = PriceData(ticker=ticker, price=price, lastPrice=0, direction="UP", reversed=False, high=price,
                           low=price)
            self.history[ticker] = pd

        pd.lastPrice = pd.price
        pd.price = price

        if pd.price >= pd.lastPrice:
            direction = "UP"
        else:
            direction = "DOWN"
        pd.reversed = direction != pd.direction
        pd.direction = direction

        if pd.price > pd.high:
            pd.high = pd.price
        if pd.price < pd.low:
            pd.low = pd.price

        return pd


def arrow(direction):
    if direction == "UP":
        return "↑"
    else:
        return "↓"


def change(old, new):
    return (old - new) / old


pt = PriceTracker()

tickers = ['ENPH', 'XLE', 'XOP', 'SPX']
prices = {}
delay = 3 * 60
# delay = 10
while True:
    print(datetime.now().strftime('%H:%M:%S'))
    response = tdlogin(redirect=redirect, consumer_key=consumer_key, username=username, password=password)

    access_token = response['access_token']
    # print(access_token)

    tdclient = TDClient(access_token)
    for ticker in tickers:
        quote = tdclient.quote(ticker)
        price = quote[ticker]["lastPrice"]
        pd = pt.add(ticker, price)
        if pd.direction == "UP":
            c = change(pd.low, pd.price)
        else:  # down
            c = change(pd.high, pd.price)
        cp = c * 100
        r = ""
        if pd.reversed:
            r = "REVERSED"
        print(f"{ticker}: {price} " + arrow(pd.direction) + f" ({cp}%) {r}")

    time.sleep(delay)
