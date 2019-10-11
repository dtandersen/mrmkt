# import json
import json
import ssl
import time
from dataclasses import dataclass

import websocket

from mrmkt.common.config import read_config

@dataclass
class Event:
    bid: float
    mid: float
    ask: float


class Buyer:
    def __init__(self):
        self.buy_stock = False
        self.sell_stock = False
        self.price = -1

    def handle(self, event: Event):
        if self.buy_stock and self.price == -1:
            print(f"Bought for ${event.ask}")
            self.price = event.ask
            self.buy_stock = False
        elif self.sell_stock and self.price != -1:
            profit = event.bid - self.price
            print(f"Sold for ${event.bid}, purchased for ${self.price}, profit ${profit}")
            self.price = -1
            self.sell_stock = False

    def buy(self):
        if not self.buy_stock and self.price == -1:
            print("Created buy order")
            self.buy_stock = True

    def sell(self):
        if not self.sell_stock and self.price != -1:
            print("Created sell order")
            self.sell_stock = True


class Handler:
    def __init__(self, buyer: Buyer):
        self.buyer = buyer
        self.prices = []
        self.last_time = time.time()
        self.old_avg = 0

    def handle(self, event: Event):
        if event.mid is not None:
            self.add(float(event.mid))

        if time.time() > self.last_time + 60:
            new_avg = self.avg_price()
            self.print_price(new_avg, self.old_avg)
            if new_avg > self.old_avg:
                self.buyer.buy()
            elif new_avg < self.old_avg:
                self.buyer.sell()

            self.old_avg = new_avg
            self.prices = []
            self.last_time = time.time()

    def add(self, price: float):
        self.prices.append(price)

    def print_price(self, current_price: float, last_price: float):
        ravg = round(last_price, 10)
        rounded_current_price = round(current_price, 10)
        p1 = last_price
        p2 = current_price
        try:
            c = 100 * price_diff(p1, p2)
        except ZeroDivisionError:
            c = 0
        cr = round(c, 3)
        print(f"current: {rounded_current_price}  average: {ravg}  change: {cr}%")

    def avg_price(self):
        return sum(self.prices) / len(self.prices)


def price_diff(old_price, new_price):
    return (new_price - old_price) / old_price


class Piper:
    def go(self):
        config = read_config()
        api_key = config['tiingo']['api_key']
        ws = websocket.create_connection(f"wss://api.tiingo.com/iex?{api_key}")

        subscribe = {
            'eventName': 'subscribe',
            'authorization': api_key,
            'eventData': {
                'thresholdLevel': 0,
                'tickers': ['spxl', 'spy']
            }
        }
        buyer = Buyer()
        h = Handler(buyer)
        ws.send(json.dumps(subscribe))
        while True:
            # print(ws.recv())
            d = ws.recv()
            jsond = json.loads(d)
            if "service" not in jsond:
                continue
            if jsond["service"] != "iex":
                continue
            e = Event(
                bid=jsond["data"][5],
                mid=jsond["data"][6],
                ask=jsond["data"][7]
            )
            if e.ask is None or e.mid is None or e.bid is None:
                continue
            # print(d)
            try:
                h.handle(e)
                buyer.handle(e)
            except Exception as e:
                print(d)
                raise e


if __name__ == "__main__":
    p = Piper()
    p.go()