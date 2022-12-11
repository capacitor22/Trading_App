import matplotlib.pyplot as plt
import mplfinance as mpf
import base64
from io import BytesIO, StringIO

def get_graph():
    buffer=BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png=buffer.getvalue()
    graph=base64.b64encode(image_png)
    graph=graph.decode('utf-8')
    buffer.close()
    return graph


def get_plot(x,y):
    plt.switch_backend('AGG')
    plt.figure(figsize=(10,5))
    plt.title('sales...')
    plt.plot(x,y)
    plt.xticks(rotation=45)
    plt.xlabel('item')
    plt.ylabel('price')
    plt.tight_layout()
    graph=get_graph()
    return graph

def get_candlegraph():
    buffer=StringIO()
    mpf.savefig(buffer, format='svg')
    buffer.seek(0)
    graph=buffer.getvalue()
    buffer.close()
    return graph
    

def get_candleplot(prices):
    mpf.switch_backend('AGG')
    mpf.figure(figsize=(10,5))
    mpf.title('Candlestick')
    mpf.plot(prices, type='candle', volume=True)
    mpf.xticks(rotation=45)
    mpf.xlabel('Date')
    mpf.ylabel('Price')
    mpf.tight_layout()
    graph=get_candlegraph()
    return graph


### Indicators
def movingAverage(ma, prices):
    sum = 0
    if len(prices)<ma:
        return None
    else:
        prices = prices[-ma:]
        for i in range(1, ma):
            sum += prices[i].close
        return sum/ma


### Trade Signs
def is_bullish_candlestick(candle):
    return candle.close > candle.open

def is_bearish_engulfing(candles, index):
    current_candle = candles[index]
    previous_candle = candles[index-1]

    if is_bullish_candlestick(previous_candle) \
        and current_candle.close < previous_candle.open \
        and current_candle.open > previous_candle.close:
        return True
    return False

def is_bearisn_candlestick(candle):
    return candle.close < candle.open

def is_bullish_engulfing(candles, index):
    current_candle = candles[index]
    previous_candle = candles[index-1]

    if is_bearisn_candlestick(previous_candle) \
        and current_candle.close > previous_candle.open \
        and current_candle.open < previous_candle.close:
        return True
    return False

def deathCross():
    pass

def goldenCross():
    pass