import csv
from datetime import date, timedelta

import mrmkt
from mrmkt.indicator.sortino import SortinoIndicator

repo = mrmkt.ext.postgresx()
# iex, nyse arca, bats, NASDAQ, NYSE
tickers = []
with open('tickers.csv') as csvfile:
    readCSV = csv.reader(csvfile, delimiter=',')
    for row in readCSV:
        tickers.append(row[0])
res = []
count = 0
end = date.today()
start = end - timedelta(days=365 * 2)
print(f"{start} => {end}")
exit(0)
for ticker in tickers:
    try:
        price_data = repo.list_prices(ticker, start=start, end=end)
        if len(price_data) == 0:
            continue
        if not price_data[-1].date == end:
            print(f"{ticker} rejected: not updated since " + str(price_data[-1].date))
            continue
        # history_start = end - timedelta(days=365*2)
        history_start = start
        if price_data[0].date > history_start:
            print(f"{ticker} rejected: insufficient historical data actual:" + str(
                price_data[0].date) + ", expected: " + str(history_start))
            continue
        # if not price_data[0].volume > 1000:
        #     print(f"{ticker} rejected: low volume " + str(price_data[0].volume))
        #     continue
        close = list(filter(lambda p: p.date >= start, price_data))
        if not close[0].date == start:
            print(f"{ticker} rejected: invalid start date " + str(close[0].date))
            continue
        close = list(map(lambda p: p.close, price_data))
        p = []
        # print(close)
        for i in range(0, len(close) - 1):
            # print(i)
            # https://finance.zacks.com/calculate-percentage-increase-stock-value-2648.html
            p1 = close[i]  # old price
            p2 = close[i + 1]  # new price
            p.append((p2 - p1) / p1)

        # print(close)
        # print(p)
        # exit(0)
        sortino30 = SortinoIndicator(0.00 ** (1 / 30))
        p30 = p[-30:]
        ratio30 = sortino30.go(p30)
        # if not ratio > 0:
        #     print(f"{ticker} rejected: unstable: {ratio}")
        #     continue

        sortino = SortinoIndicator((1.15 ** (1 / 252)) - 1)
        ratio = sortino.go(p)
        res.append({
            "ticker": ticker,
            "ratio": ratio,
            "ratio30": ratio30
        })
    except ZeroDivisionError:
        pass
    count = count + 1
# print(res)
res.sort(key=lambda x: x['ratio'], reverse=False)
for z in res:
    print(f"{z['ticker']} => {z['ratio']}, {z['ratio30']}")
print(count)
