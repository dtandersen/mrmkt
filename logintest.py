import yaml

from atradeauth import tdlogin
from tdameritrade import TDClient


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

response = tdlogin(redirect=redirect, consumer_key=consumer_key, username=username, password=password)
print(response)
access_token = response['access_token']

c = TDClient(access_token)
print(c.accounts())
