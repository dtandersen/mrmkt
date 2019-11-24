import json

from websocket import create_connection
# import simplejson as json
ws = create_connection("wss://api.tiingo.com/iex")

subscribe = {
        'eventName':'subscribe',
        'authorization':'',
        'eventData': {
            'thresholdLevel': 0,
            'tickers': ['EURUSD']
    }
}

ws.send(json.dumps(subscribe))
while True:
    print(ws.recv())