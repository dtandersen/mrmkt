import time
from typing import List

import yaml

from atradeauth import tdlogin
from tdameritrade import TDClient
from datetime import datetime

from strategy import EMA8Strategy, Trader, Strategy


def read_portfolio(my_file):
    tickers = [line.rstrip() for line in open(my_file)]
    return tickers


def get_td_client() -> TDClient:
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
    tdclient = None
    while tdclient is None:
        try:
            response = tdlogin(redirect=redirect, consumer_key=consumer_key, username=username, password=password)
            access_token = response['access_token']
            tdclient = TDClient(access_token)
        except KeyError as e:
            print(e)

    return tdclient


def create_strategy(tickers: List, trader: Trader) -> List[Strategy]:
    strats = []
    for ticker in tickers:
        strat = EMA8Strategy(ticker, trader)
        strats.append(strat)
    return strats


class EMA8Strategy(Strategy):
    def trade(self):
        pass


class TDTrader(Trader):
    def get_client(self) -> TDClient:
        return get_td_client()

    def ema15min8(self):
        client = get_td_client()
        client.history()

tickers = read_portfolio("portfolio.txt")
prices = {}

delay = 15 * 60
# delay = 10
while True:
    rawt = datetime.now()
    t_in_s = rawt.hour * 3600 + rawt.minute * 60 + rawt.second
    if t_in_s % delay > 0:
        time.sleep(1)
        continue
    print(rawt.strftime('%H:%M:%S'))
    tdclient = get_td_client()
    # print(access_token)

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

    # time.sleep(delay)
