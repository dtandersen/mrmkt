import requests

headers = {
        'Content-Type': 'application/json'
        }
requestResponse = requests.get("https://api.tiingo.com/tiingo/daily/goog/prices?startDate=2019-07-12&token=fd6ce0ce784cf699ea6b9b74746b5ea7eddfd2fe",
                                    headers=headers)
print(requestResponse.json())