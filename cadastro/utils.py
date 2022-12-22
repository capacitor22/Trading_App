
### Trading Patterns
def is_bullish_candlestick(candle):
    return candle.close > candle.open

def is_bearisn_candlestick(candle):
    return candle.close < candle.open


def is_bearish_engulfing(candles, index):
    current_candle = candles[index]
    previous_candle = candles[index-1]

    if is_bullish_candlestick(previous_candle) \
        and current_candle.close < previous_candle.open \
        and current_candle.open > previous_candle.close:
        return True
    return False

def is_bullish_engulfing(candles, index):
    current_candle = candles[index]
    previous_candle = candles[index-1]

    if is_bearisn_candlestick(previous_candle) \
        and current_candle.close > previous_candle.open \
        and current_candle.open < previous_candle.close:
        return True
    return False

def cross(candles, index, fast_ma, slow_ma):
    current_candle = candles[index]
    previous_candle = candles[index-1]

    if fast_ma == 'ma9':
        fastp = previous_candle.ma9 
        fast = current_candle.ma9 
    elif fast_ma == 'ma20':
        fastp = previous_candle.ma20 
        fast = current_candle.ma20 
    elif fast_ma == 'ma50':
        fastp = previous_candle.ma50 
        fast = current_candle.ma50 
    else:
        return 0

    if slow_ma == 'ma20':
        slowp = previous_candle.ma20 
        slow = current_candle.ma20
    elif slow_ma == 'ma50':
        slowp = previous_candle.ma50 
        slow = current_candle.ma50
    elif slow_ma == 'ma200':
        slowp = previous_candle.ma200 
        slow = current_candle.ma200
    else:
        return 0

    if fastp != None and slowp != None and fast != None and slow != None:
        if fastp < slowp and fast > slow:
            # print("============")  
            # print("current_candle.date", current_candle.date)  
            # print("Fastp = ", fastp)
            # print("Slowp = ", slowp)
            # print("Fast = ", fast)
            # print("Slow = ", slow)
            return 1
        elif fastp > slowp and fast < slow:
            # print("============")    
            # print("current_candle.date", current_candle.date)  
            # print("Fastp = ", fastp)
            # print("Slowp = ", slowp)
            # print("Fast = ", fast)
            # print("Slow = ", slow)
            return -1
        else:
            return 0
    return 0