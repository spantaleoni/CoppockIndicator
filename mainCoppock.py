#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Dec  4 13:36:41 2022

@author: simonlesflex
"""

# IMPORTING PACKAGES

import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import floor
from termcolor import colored as cl
from datetime import date, time, timedelta
import quantstats as qs
import yfinance as yf



plt.style.use('fivethirtyeight')
plt.rcParams['figure.figsize'] = (20,10)

G_BACKDAYS = 25 * 252
G_EQIND = 'SPY'
start = date.today() - timedelta(days=G_BACKDAYS)
end = date.today()
# EXTRACTING STOCK DATA

spydf = yf.download(G_EQIND, start=start, end=end)
benchmarkret_df = spydf['Adj Close'].pct_change()
print(spydf.tail())
spydf = spydf.shift()


# COPPOCK CURVE CALCULATION

def wma(data, lookback):
    weights = np.arange(1, lookback + 1)
    val = data.rolling(lookback)
    wma = val.apply(lambda prices: np.dot(prices, weights) / weights.sum(), raw = True)
    return wma

def get_roc(close, n):
    difference = close.diff(n)
    nprev_values = close.shift(n)
    roc = (difference / nprev_values) * 100
    return roc

def get_cc(data, roc1_n, roc2_n, wma_lookback):
    longROC = get_roc(data, roc1_n)
    shortROC = get_roc(data, roc2_n)
    ROC = longROC + shortROC
    #ROC = longROC - shortROC
    cc = wma(ROC, wma_lookback)
    return cc

#spydf['Coppock'] = get_cc(spydf['Adj Close'], 64, 10, 21)
spydf['Coppock'] = get_cc(spydf['Adj Close'], 64, 10, 21)
spydf = spydf.dropna()
print(spydf.tail())

spydf.drop(['Open', 'High', 'Low', 'Close', 'Volume'], axis=1, inplace=True)

spydf.plot(label='S&P500')
plt.show()



# COPPOCK CURVE STRATEGY

def implement_cc_strategy(prices, cc):
    buy_price = []
    sell_price = []
    cc_signal = []
    signal = 0
    
    for i in range(len(prices)):
        #if cc[i-4] < 0 and cc[i-3] < 0 and cc[i-2] < 0 and cc[i-1] < 0 and cc[i] > 0:
        if cc[i-3] < -2 and cc[i-2] < -2 and cc[i-1] < -2 and cc[i] > -2:
            if signal != 1:
                buy_price.append(prices[i])
                sell_price.append(np.nan)
                signal = 1
                cc_signal.append(signal)
            else:
                buy_price.append(np.nan)
                sell_price.append(np.nan)
                cc_signal.append(0)
        #elif cc[i-4] > 0 and cc[i-3] > 0 and cc[i-2] > 0 and cc[i-1] > 0 and cc[i] < 0:
        elif cc[i-3] > -2 and cc[i-2] > -2 and cc[i-1] > -2 and cc[i] < -2:
        #elif cc[i-4] > cc[i-3] and cc[i-3] > cc[i-2] and cc[i-2] > cc[i-1] and cc[i-1] > cc[i] and cc[i] < 0:
            if signal != -1:
                buy_price.append(np.nan)
                sell_price.append(prices[i])
                signal = -1
                #cc_signal.append(signal)
                cc_signal.append(signal)
            else:
                buy_price.append(np.nan)
                sell_price.append(np.nan)
                cc_signal.append(0)
        else:
            buy_price.append(np.nan)
            sell_price.append(np.nan)
            cc_signal.append(0)
            
    return buy_price, sell_price, cc_signal

buy_price, sell_price, cc_signal = implement_cc_strategy(spydf['Adj Close'], spydf['Coppock'])


# COPPOCK CURVE TRADING SIGNAL PLOT

ax1 = plt.subplot2grid((15,1), (0,0), rowspan = 5, colspan = 1)
ax2 = plt.subplot2grid((15,1), (6,0), rowspan = 6, colspan = 1)
ax1.plot(spydf['Adj Close'], linewidth = 2, label = 'S&P500')
ax1.plot(spydf.index, buy_price, marker = '^', color = 'green', markersize = 12, linewidth = 0, label = 'BUY SIGNAL')
ax1.plot(spydf.index, sell_price, marker = 'v', color = 'r', markersize = 12, linewidth = 0, label = 'SELL SIGNAL')
ax1.legend()
ax1.set_title('S&P500 Coppock TRADING SIGNALS')
for i in range(len(spydf)):
    if spydf.iloc[i, 1] >= 0:  #Coppock >= 0
        ax2.bar(spydf.iloc[i].name, spydf.iloc[i, 1], color = '#009688')
    else:    
        ax2.bar(spydf.iloc[i].name, spydf.iloc[i, 1], color = '#f44336')
ax2.set_title('S&P500 Coppock Curve')
plt.show()



# STOCK POSITION

position = []
for i in range(len(cc_signal)):
    if cc_signal[i] > 1:
        position.append(0)
    else:
        position.append(1)
        
for i in range(len(spydf['Adj Close'])):
    if cc_signal[i] == 1:
        position[i] = 1
    elif cc_signal[i] == -1:
        position[i] = 0
        #position[i] = -1
    else:
        position[i] = position[i-1]
        
close_price = spydf['Adj Close']
cc = spydf['Coppock']
cc_signal = pd.DataFrame(cc_signal).rename(columns = {0:'cc_signal'}).set_index(spydf.index)
position = pd.DataFrame(position).rename(columns = {0:'cc_position'}).set_index(spydf.index)

frames = [close_price, cc, cc_signal, position]
strategy = pd.concat(frames, join = 'inner', axis = 1)

print(strategy)



# BACKTESTING

#spy_ret = pd.DataFrame(np.diff(spydf['Adj Close'])).rename(columns = {0:'returns'})
spy_ret = pd.DataFrame(spydf['Adj Close'].pct_change().rename('returns'))
spy_ret.dropna(inplace=True)
spylen = len(spy_ret) - 1
#spy_ret = spy_ret.set_index(spydf.index[-(spylen):])
cc_strategy_ret = []

for i in range(len(spy_ret)):
    returns = spy_ret['returns'][i]*strategy['cc_position'][i]
    cc_strategy_ret.append(returns)
    
cc_strategy_ret_df = pd.DataFrame(cc_strategy_ret).rename(columns = {0:'Returns'})
cc_strategy_ret_df = cc_strategy_ret_df.set_index(spy_ret.index)
investment_value = 100000
number_of_stocks = floor(investment_value/spydf['Adj Close'][0])
cc_investment_ret = []

for i in range(len(cc_strategy_ret_df['Returns'])):
    returns = number_of_stocks*cc_strategy_ret_df['Returns'][i]
    cc_investment_ret.append(returns)

cc_investment_ret_df = pd.DataFrame(cc_investment_ret).rename(columns = {0:'investment_returns'})
cc_investment_ret_df = cc_investment_ret_df.set_index(spy_ret.index)
total_investment_ret = round(sum(cc_investment_ret_df['investment_returns']), 2)
profit_percentage = floor((total_investment_ret/investment_value)*100)
print(cl('Profit gained from the COPPOCK strategy by investing $100k in S&P500 : {}'.format(total_investment_ret), attrs = ['bold']))
print(cl('Profit percentage of the COPPOCK strategy : {}%'.format(profit_percentage), attrs = ['bold']))


cc_strategy_ret_df['Benchmark'] = (
    (benchmarkret_df)
)
qs.reports.full(cc_strategy_ret_df['Returns'], cc_strategy_ret_df['Benchmark'])