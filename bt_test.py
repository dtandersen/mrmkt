from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import math

import pandas_datareader.data as pdr
import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt

from mrmkt.common.config import read_config


class TestStake(bt.Sizer):
	params = (('stake', 1),)

	def _getsizing(self, comminfo, cash, data, isbuy):
		if isbuy:
			divide = math.floor(cash/data.close[0])
			self.p.stake = divide
			return self.p.stake

		# Sell situation
		position = self.broker.getposition(data)
		if not position.size:
			return 0  # do not sell if nothing is open

		return self.p.stake


class maxRiskSizer(bt.Sizer):
    '''
    Returns the number of shares rounded down that can be purchased for the
    max rish tolerance
    '''
    params = (('risk', .5),)

    def __init__(self):
        if self.p.risk > 1 or self.p.risk < 0:
            raise ValueError('The risk parameter is a percentage which must be'
                'entered as a float. e.g. 0.5')

    def _getsizing(self, comminfo, cash, data, isbuy):
        # Strategy Method example
        pos = self.strategy.getposition(data)
        # Broker Methods example
        acc_value = self.broker.getvalue()

        # Print results
        print('----------- SIZING INFO START -----------')
        print('--- Strategy method example')
        print(pos)
        print('--- Broker method example')
        print('Account Value: {}'.format(acc_value))
        print('--- Param Values')
        print('Cash: {}'.format(cash))
        print('isbuy??: {}'.format(isbuy))
        print('data[0]: {}'.format(data[0]))
        print('------------ SIZING INFO END------------')
        if isbuy == True:
            size = math.floor((cash * self.p.risk) / data[0])
        else:
            size = math.floor((cash * self.p.risk) / data[0]) * -1
        return size

# Create a Stratey
class TestStrategy(bt.Strategy):
    params = dict(
        stop_loss=0.005,  # price is 2% less than the entry point
        trail=False,
    )

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders
        self.order = None
        sma_fast = bt.indicators.SMA(period=3)
        sma_slow = bt.indicators.SMA(period=13)
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=14)
        self.rsi_sma = bt.indicators.SMA(self.rsi, period=7)
        # self.ind = smafast > smaslow
        #self.ind =  smaslow - smafast
        # sma_fast = self.p._movav(period=self.p.fast)
        # sma_slow = self.p._movav(period=self.p.slow)

        # self.buysig = bt.indicators.CrossOver(sma_fast, sma_slow)
        self.buysig = bt.indicators.CrossOver(self.rsi_sma, self.rsi)
        self.maxprice = -1


    def notify_order(self, order):
        if not order.status == order.Completed:
            return  # discard any other notification
        # if order.status in [order.Submitted, order.Accepted]:
        #     # Buy/Sell order submitted/accepted to/by broker - Nothing to do
        #     return
        # print(order.status)
        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY {order.executed.size} @ ${order.executed.price:.2f}')

                # if not self.p.trail:
                stop_price = order.executed.price * (1.0 - self.p.stop_loss)
                self.sell(exectype=bt.Order.Stop, price=stop_price)
                # else:
                #     self.sell(exectype=bt.Order.StopTrail, trailamount=self.p.trail)
            elif order.issell():
                self.log(f'SELL {order.executed.size} @ ${order.executed.price:.2f}')
                # self.log('SELL EXECUTED, %d' % order.executed.size)

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def next(self):
        # if self.buysig > 0:
        #     print(f"rsi: {self.rsi[0]:.0f}  signal: {self.buysig[0]}")
        # print(f"rsi: {self.position}")
        if not self.position:
            # if self.rsi < 33 and self.buysig > 0:
            if self.rsi < 33 and self.rsi[-1] > self.rsi[-2]:
                print(f"rsi: {self.rsi[0]:.0f}  signal: {self.buysig[0]}")
                self.buy()
                self.maxprice = -1
        else:
            if self.data.close > self.maxprice:
                self.maxprice = self.data.close
            if self.data.close < self.maxprice * .995:
                self.sell()
            if self.rsi > 66 and self.rsi[-1] < self.rsi[-2]:
                print(f"rsi: {self.rsi[0]:.0f}  signal: {self.buysig[0]}")
            # if self.buysig < 0:
            # if self.rsi > 66.6 or self.buysig < 0:
                self.sell()
        # if self.position:
        #     print("has position")
        #     return
        # if self.rsi > 66:
        #     self.sell()
        # else:
        #     # if self.ind[0] < 0:
        #     if self.rsi < 33: # and self.ind > 0:
        #         self.buy()
        return
        # Simply log the closing price of the series from the reference
        # self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.dataclose[0] < self.dataclose[-1]:
                    # current close less than previous close

                    if self.dataclose[-1] < self.dataclose[-2]:
                        # previous close less than the previous close

                        # BUY, BUY, BUY!!! (with default parameters)
                        self.log('BUY CREATE, %.2f' % self.dataclose[0])

                        # Keep track of the created order to avoid a 2nd order
                        self.order = self.buy()

        else:

            # Already in the market ... we might sell
            if len(self) >= (self.bar_executed + 5):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()


if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(TestStrategy)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, 'datas/orcl-1995-2014.txt')

    s="SPY"
    config=read_config()
    ddd = datetime.datetime(2019, 9, 9)
    df = pdr.get_iex_data_tiingo(s, ddd, ddd, api_key=config["tiingo"]["api_key"], freq="1min")
    print(df)
    df = df.loc[s]
    # df = df.drop(['high', 'close', 'low', 'open'], axis=1)
    df.columns = ['close', 'high', 'low', 'open'] #, 'adjVolume', 'splitFactor', 'volume']
    d={}
    d["data" + str(s)] = bt.feeds.PandasData(dataname=df, timeframe=bt.TimeFrame.Minutes, openinterest=None)
    data = d["data" + str(s)]

    # # Create a Data Feed
    # data = bt.feeds.YahooFinanceCSVData(
    #     dataname=datapath,
    #     # Do not pass values before this date
    #     fromdate=datetime.datetime(2000, 1, 1),
    #     # Do not pass values before this date
    #     todate=datetime.datetime(2000, 12, 31),
    #     # Do not pass values after this date
    #     reverse=False)
    # Add the Data Feed to Cerebro
    cerebro.adddata(data, name=s)

    # Set our desired cash start
    cerebro.broker.setcash(25000.0)
    cerebro.broker.setcommission(commission=0)
    cerebro.addsizer(TestStake)
    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())