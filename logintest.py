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

token_generator = TokenGenerator(redirect, consumer_key, username, password)
client = TDAmeritradeClient(token_generator)
response = token_generator.authenticate()
print(response)
access_token = response['access_token']

c = TDClient(access_token)
print(c.accounts())
