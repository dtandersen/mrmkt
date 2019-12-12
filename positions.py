import yaml

from tdameritrade import TDClient

from mrmkt.ext.tdameritrade import TDAmeritradeClient, TokenGenerator


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

print(f"Ticker  Shares  Price     Cost Basis    %")

portfolio = client.list_positions(accountid)
positions = portfolio.positions
for p in positions:
    cost_basis = p.shares * p.price
    pct = cost_basis / portfolio.equity * 100
    print(f"{p.symbol:<6}  {p.shares:6.0f}  ${p.price:5.2f}  ${cost_basis:5.2f}  {pct:3.2f}%")