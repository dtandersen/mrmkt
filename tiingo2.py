import requests

headers = {
        'Content-Type': 'application/json'
        }
requestResponse = requests.get("https://api.tiingo.com/tiingo/daily/goog/prices?startDate=2019-07-12&token=",
                                    headers=headers)
print(requestResponse.json())