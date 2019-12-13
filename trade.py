from dataclasses import asdict

import yaml

from tdameritrade import TDClient

from mrmkt.ext.tdameritrade import TDAmeritradeClient, TokenGenerator
import pandas as pd
import numpy as np

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
account = ameritrade["accounts"][0]
accountid = account["accountid"]

token_generator = TokenGenerator(redirect, consumer_key, username, password)
client = TDAmeritradeClient(token_generator)
print(token_generator.access_token())
print(f"Ticker  Shares  Price     Cost Basis    %")

portfolio = client.list_positions(accountid)
positions = portfolio.positions
for p in positions:
    symbol = p.symbol
    prices = client.history(symbol)
    df = pd.DataFrame([asdict(p) for p in prices])
    df.set_index("datetime")
    df.sort_index()
    ewmaName = "ema8"
    df[ewmaName] = df["close"].ewm(span=8, adjust=False).mean()
    # df['position'] = df['close'] > df['ema8']
    # df['pre_position'] = df['position'].shift(1)
    # df.dropna(inplace=True)  # dropping the NaN values
    # df['crossover'] = np.where(df['position'] == df['pre_position'], False, True)
    df["diff"] = df["close"] - df["ema8"]
    print(symbol)
    pd.set_option('display.width', 200)
    pd.set_option('display.max_columns', 10)
    # df['time'] = df['datetime'].dt.strftime('%m/%d/%Y %H:%M')
    df["time"] = df["datetime"].dt.tz_convert('US/Eastern')
    simple = df[['close', "ema8", 'time', 'diff']].tail(3)
    # x0 = simple.iloc[-2]
    # x1 = simple.iloc[-1]
    print(simple)
    diff = simple["diff"].to_numpy()
    if diff[-3] < 0 and diff[-2] > 0:
        print("buy")
    elif diff[-3] > 0 and diff[-2] < 0:
        print("sell")
    # print(df.to_string())
    # print(df)
    # cost_basis = p.shares * p.price
    # pct = cost_basis / portfolio.equity * 100
    # print(f"{p.symbol:<6}  {p.shares:6.0f}  ${p.price:5.2f}  ${cost_basis:5.2f}  {pct:3.2f}%")
    # exit()