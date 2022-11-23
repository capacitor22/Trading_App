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