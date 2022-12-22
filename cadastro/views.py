from alpaca_trade_api.rest import TimeFrame, TimeFrameUnit
from datetime import date, timedelta, datetime
import decimal
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views.generic.list import ListView
from django.urls import reverse_lazy
from io import StringIO

import alpaca_trade_api as tradeapi
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests, json
import tulipy as ti
# import talib
import numpy as np

from config import *
from .models import stock, stock_price, detected_patterns, watch_list
from .forms import CustomCriaUsuarioForm
from .utils import is_bullish_engulfing, is_bearish_engulfing, cross

ACCOUNT_URL = "{}/v2/account".format(BASE_URL)
ORDERS_URL = "{}/v2/orders".format(BASE_URL)
POSITIONS_URL = "{}/v2/positions".format(BASE_URL)
ASSETS_URL = "{}/v2/assets".format(BASE_URL)
HEADERS = {'APCA-API-KEY-ID':API_KEY, 'APCA-API-SECRET-KEY':SECRET_KEY}

def RegistrarUsuario(request):
    if request.method == "GET":
        return render(
            request, "cadastro/usermanagement/login.html",
            {"form": CustomCriaUsuarioForm, 'titulo': 'Cria Novo Usuário', "botao": "Criar"}
        )
    elif request.method == "POST":
        form = CustomCriaUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect(reverse_lazy("PaginaInicial.html"))

def Inicio(request):
    if request.user.is_authenticated:
        account = requests.get(ACCOUNT_URL, headers=HEADERS)
        # OBS: account é um dicionário mas os outros são listas de dicionarios, entao precisa adaptar
        if account:
            accout_json = account.json()
        orders = requests.get(ORDERS_URL, headers=HEADERS)
        if orders:
            orders_json = orders.json()
        positions = requests.get(POSITIONS_URL, headers=HEADERS)
        if positions:
            positions_json = positions.json()
        context = {'titulo': 'Alpaca Account','account': accout_json, 'orders': orders_json, 'positions':positions_json}
        return render(request, "PaginaInicial.html", context)
    else:
        return redirect(reverse_lazy("cadastro:login"))


def AlpacaShowAccount(request):
    account = requests.get(ACCOUNT_URL, headers=HEADERS)
    # OBS: account é um dicionário mas os outros são listas de dicionarios, entao precisa adaptar
    if account:
        accout_json = account.json()
    orders = requests.get(ORDERS_URL, headers=HEADERS)
    if orders:
        orders_json = orders.json()
    positions = requests.get(POSITIONS_URL, headers=HEADERS)
    if positions:
        positions_json = positions.json()
    context = {'titulo': 'Painel Inicial','account': accout_json, 'orders': orders_json, 'positions':positions_json}
    return render(request, "PaginaInicial.html", context)


class ListStocks(LoginRequiredMixin, ListView):
    # login_url = reverse_lazy('acesso:login')
    model = stock
    template_name = 'cadastro/listas/stocks.html'


def ImportStocksAlpaca(request):
    api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)
    assets = api.list_assets()
    processed = active_and_tradable = imported = updated = 0

    for asset in assets:
        processed += 1
        if asset.status == 'active' and asset.tradable:
            active_and_tradable += 1
            obj, created = stock.objects.update_or_create(
                id_alpaca = asset.id,
                defaults={
                    'origin': 'Alpaca',
                    # 'class_alpaca': asset.class,
                    'easy_to_borrow': asset.easy_to_borrow, 'exchange': asset.exchange,
                    'fractionable': asset.fractionable, 'id_alpaca': asset.id,
                    'maintenance_margin_requirement': float(asset.maintenance_margin_requirement),
                    'marginable': asset.marginable,
                    # 'min_order_size': float(asset.min_order_size),
                    # 'min_trade_increment': float(asset.min_trade_increment),
                    'name': asset.name,
                    # 'price_increment': float(asset.price_increment),
                    'shortable': asset.shortable, 'status': asset.status,
                    'symbol': asset.symbol, 'tradable': asset.tradable
                },
            )
            if created:
                imported += 1
            else:
                updated += 1
    # print('processed = ', processed)
    # print('active_and_tradable = ', active_and_tradable)
    # print('imported = ', imported)
    # print('updated = ', updated)
    return redirect(reverse_lazy("cadastro:ListStocks"))


def ListPrices(request, pk):
    stock_obj = stock.objects.get(id=pk)
    if request.POST:
        start_date = request.POST.get('startdate', None)
        end_date = request.POST.get('enddate', None)
        timeframe = request.POST.get('timeframe', None)
        if (start_date != None) and (end_date != None) and (timeframe != None):
            UpdatePricesAlpaca([stock_obj.symbol], start_date, end_date, timeframe)
    prices = stock_price.objects.filter(stock = pk)
    context = {'prices':prices, 'stock': stock_obj}
    return render(request, "cadastro/listas/prices.html", context)


def UpdateIndicators(new_bar_ind, stock_ind, tf_ind):
    prices_ind = stock_price.objects.filter(stock=stock_ind, timeframe=tf_ind, date__lt=new_bar_ind.t)
    recent_closes = [float(bar.close) for bar in prices_ind]
    recent_closes_t = recent_closes[-199:]
    recent_closes_200 = recent_closes[-199:]
    recent_closes_50 = recent_closes[-49:]
    recent_closes_20 = recent_closes[-19:]
    recent_closes_9 = recent_closes[-8:]
    recent_closes_t.append(new_bar_ind.c)
    recent_closes_200.append(new_bar_ind.c)
    recent_closes_50.append(new_bar_ind.c)
    recent_closes_20.append(new_bar_ind.c)
    recent_closes_9.append(new_bar_ind.c)
    data = np.array(recent_closes_t)
    data_200 = np.array(recent_closes_200)
    data_50 = np.array(recent_closes_50)
    data_20 = np.array(recent_closes_20)
    data_9 = np.array(recent_closes_9)
    if len(data_200)>199:
        rma200 = ti.sma(data_200, period=200)
        rma50 = ti.sma(data_50, period=50)
        rma20 = ti.sma(data_20, period=20)
        rma9 = ti.sma(data_9, period=9)
        ma200 = rma200[0]
        ma50 = rma50[0]
        ma20 = rma20[0]
        ma9 = rma9[0]
        bb = ti.bbands(data_20, period=20, stddev=2)
        bbh = bb[0][0] 
        bbmm = bb[1][0] 
        bbl = bb[2][0] 
    elif len(data_50)>49:             
        ma200 = None
        rma50 = ti.sma(data_50, period=50)
        rma20 = ti.sma(data_20, period=20)
        rma9 = ti.sma(data_9, period=9)
        ma50 = rma50[0]
        ma20 = rma20[0]
        ma9 = rma9[0]
        bb = ti.bbands(data_20, period=20, stddev=2)
        bbh = bb[0][0] 
        bbmm = bb[1][0] 
        bbl = bb[2][0] 
    elif len(data)>19:             
        ma200 = None
        ma50 = None
        rma20 = ti.sma(data_20, period=20)
        rma9 = ti.sma(data_9, period=9)
        ma20 = rma20[0]
        ma9 = rma9[0]
        bb = ti.bbands(data_20, period=20, stddev=2)
        bbh = bb[0][0] 
        bbmm = bb[1][0] 
        bbl = bb[2][0] 
    elif len(data)>8:             
        rma9 = ti.sma(data_9, period=9)
        ma9 = rma9[0]
        ma200 = ma50 = ma20 = bbh = bbmm = bbl = None
    else:
        ma200 = ma50 = ma20 = ma9 = bbh = bbmm = bbl = None
    
    return [ma9, ma20, ma50, ma200, bbh, bbmm, bbl] 

def InsertBarsIntoDB(new_bars, new_timeframe):
    for bar in new_bars:
        # print('Symbol = {} - Timeframe = {} - DateTime = {}', bar.S, new_timeframe, bar.t)
        # Importante: a variavel bar.S abaixo só existe se a API for consultada tendo uma lista de simbolos como entrada
        # Se a consulta for feita para apenas 1 simbolo, o parametro S de bar não é informado o que ocasionará um erro nesse ponto
        # Por isso, tanto a chamada de UpdatePricesAlpaca quanto UpdatePricesAlpacaOneStock precisam passar uma lista de simbolos como parametro, mesmo que seja uma lista unitária
        thisStock = stock.objects.get(symbol=bar.S)
        ma9 = ma20 = ma50 = ma200 = bbh = bbmm = bbl = None
        ma9, ma20, ma50, ma200, bbh, bbmm, bbl = UpdateIndicators(bar, thisStock, new_timeframe)
        obj, created = stock_price.objects.update_or_create(
            stock = thisStock,
            timeframe = new_timeframe,
            date = bar.t,
            defaults={
                'open': decimal.Decimal(bar.o), 'high': decimal.Decimal(bar.h), 'low': decimal.Decimal(bar.l), 
                'close': decimal.Decimal(bar.c), 'volume': decimal.Decimal(bar.v),
                'ma9': ma9, 'ma20': ma20, 'ma50': ma50, 'ma200': ma200, 'bbh': bbh, 'bbmm': bbmm, 'bbl': bbl
            },
        )

def UpdatePricesAlpacaOneStock(symbol, start_date=None, end_date=None, timeframe='ALL'):
    api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)    
    bars = barsM = barsW = barsD = barsH = bars5Min = None
    today=date.today()
    yesterday=date.today()-timedelta(1)
    last_month=date.today()-timedelta(weeks=5)
    last_week=date.today()-timedelta(weeks=1)
    last_hour=date.today()-timedelta(hours=1)
    last_minute=date.today()-timedelta(minutes=1)
    # print('last_month',last_month)
    # print('last_week',last_week)
    # print('last_hour',last_hour)
    # print('last_minute',last_minute)
    td_month=timedelta(weeks = 900)
    td_week=timedelta(weeks = 201)
    td_day=timedelta(days = 260) # Descontando os FDS
    td_hour=timedelta(hours = 250)
    td_minute=timedelta(days = 2)

    thisStock = stock.objects.get(symbol=symbol[0])    
    
    # Verificar se posso tirar a end date de todos os timeframes
    # Ajustar as datas de inicio de cada opcao pois o month so esta pegando um mes enquanto as outras opcoes estao pegando 2


    if timeframe == 'Month':
        if start_date == None:
            last_month_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Month').order_by('date').last()
            if last_month_bar_in_DB:
                if last_month_bar_in_DB.date.date() >= yesterday:
                    prev_month= last_month_bar_in_DB.date.date() - timedelta(weeks = 4)
                    # bars = api.get_bars(symbol, TimeFrame.Month, prev_month, yesterday, adjustment='raw' )
                    bars = api.get_bars(symbol, TimeFrame.Month, prev_month, adjustment='raw' )
                else:
                    # bars = api.get_bars(symbol, TimeFrame.Month, last_month_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    bars = api.get_bars(symbol, TimeFrame.Month, last_month_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # bars = api.get_bars(symbol, TimeFrame.Month, yesterday-td_month, yesterday, adjustment='raw' )
                bars = api.get_bars(symbol, TimeFrame.Month, yesterday-td_month, adjustment='raw' )
        else:
            bars = api.get_bars(symbol, TimeFrame.Month, start_date, end_date, adjustment='raw' )

    elif timeframe == 'Week':
        # Week
        if start_date == None:
            last_week_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Week').order_by('date').last()
            if last_week_bar_in_DB:
                if last_week_bar_in_DB.date.date() >= yesterday:
                    prev_week= last_week_bar_in_DB.date.date() - timedelta(weeks = 1)
                    # bars = api.get_bars(symbol, TimeFrame.Week, prev_week, yesterday, adjustment='raw' )
                    bars = api.get_bars(symbol, TimeFrame.Week, prev_week, adjustment='raw' )
                else:
                    # bars = api.get_bars(symbol, TimeFrame.Week, last_week_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    bars = api.get_bars(symbol, TimeFrame.Week, last_week_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # bars = api.get_bars(symbol, TimeFrame.Week, yesterday-td_week, yesterday, adjustment='raw' )
                bars = api.get_bars(symbol, TimeFrame.Week, yesterday-td_week, adjustment='raw' )
        else:
            bars = api.get_bars(symbol, TimeFrame.Week, start_date, end_date, adjustment='raw' )

    elif timeframe == 'Day':
        # Day
        if start_date == None:
            last_day_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Day').order_by('date').last()
            # print('Yesterday = ', yesterday)
            if last_day_bar_in_DB:
                # print('Last = ', last_day_bar_in_DB.date.date())
                if last_day_bar_in_DB.date.date() >= yesterday:
                    prev_day = last_day_bar_in_DB.date.date() - timedelta(days = 1)
                    # print('Previous Day = ', prev_day)
                    # barsD = api.get_bars(symbol, TimeFrame.Day, prev_day, yesterday, adjustment='raw' )
                    bars = api.get_bars(symbol, TimeFrame.Day, prev_day, adjustment='raw' )                    
                else:
                    # print('primeiro else - last day bar anterior ao yesterday')
                    # bars = api.get_bars(symbol, TimeFrame.Day, last_day_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    bars = api.get_bars(symbol, TimeFrame.Day, last_day_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # print('segundo else - sem last day bar')
                # bars = api.get_bars(symbol, TimeFrame.Day, yesterday-td_day, yesterday, adjustment='raw' )
                bars = api.get_bars(symbol, TimeFrame.Day, yesterday-td_day, adjustment='raw' )
        else:
            # print('Else sem barras anteriores')
            bars = api.get_bars(symbol, TimeFrame.Day, start_date, end_date, adjustment='raw' ) 

    elif timeframe == 'Hour':
        # Hour
        if start_date == None:
            last_hour_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Hour').order_by('date').last()
            if last_hour_bar_in_DB:
                if last_hour_bar_in_DB.date.date() >= yesterday:    # Checar se posso substituit yesterday por now
                    prev_hour= last_hour_bar_in_DB.date.date() - timedelta(days = 1)
                    # bars = api.get_bars(symbol, TimeFrame.Hour, prev_hour, yesterday, adjustment='raw' )
                    bars = api.get_bars(symbol, TimeFrame.Hour, prev_hour, adjustment='raw' )
                else:
                    # bars = api.get_bars(symbol, TimeFrame.Hour, last_hour_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    bars = api.get_bars(symbol, TimeFrame.Hour, last_hour_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # bars = api.get_bars(symbol, TimeFrame.Hour, yesterday-td_hour, yesterday, adjustment='raw' )
                bars = api.get_bars(symbol, TimeFrame.Hour, yesterday-td_hour, adjustment='raw' )
        else:
            bars = api.get_bars(symbol, TimeFrame.Hour, start_date, end_date, adjustment='raw' )

    elif timeframe == '5Minute':
        # 5Minute
        if start_date == None:
            last_5minute_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='5Minute').order_by('date').last()
            # print('Yesterday = ', yesterday)
            if last_5minute_bar_in_DB:
                # print('Last = ', last_5minute_bar_in_DB.date.date())
                if last_5minute_bar_in_DB.date.date() >= yesterday:
                    prev_min= last_5minute_bar_in_DB.date.date()  - timedelta(minutes = 1)
                    # bars = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), prev_min, yesterday, adjustment='raw' )
                    # print('Previous Minute = ', prev_min)
                    bars = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), prev_min, adjustment='raw' )
                else:
                    # print('Primeiro Else - barra anterior ao yesterday')
                    # bars = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), last_5minute_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    bars = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), last_5minute_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # print('segundo else - sem last 5Min bar')
                # bars = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), yesterday-td_minute, yesterday, adjustment='raw' )
                bars = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), yesterday-td_minute, adjustment='raw' )
        else:
            bars = api.get_bars(symbol, TimeFrame.Minute, start_date, end_date, adjustment='raw' )

    elif timeframe == 'ALL':
        # # Month
        if start_date == None:
            last_month_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Month').order_by('date').last()
            # print('Yesterday = ', yesterday)
            if last_month_bar_in_DB:
                # print('Last = ', last_month_bar_in_DB.date.date())
                if last_month_bar_in_DB.date.date() >= yesterday:
                    prev_month= last_month_bar_in_DB.date.date() - timedelta(weeks = 4)
                    # print('Previous month = ', prev_month)
                    # barsM = api.get_bars(symbol, TimeFrame.Month, prev_month, yesterday, adjustment='raw' )
                    barsM = api.get_bars(symbol, TimeFrame.Month, prev_month, adjustment='raw' )
                else:
                    # print('primeiro else - last month bar anterior ao yesterday')
                    # barsM = api.get_bars(symbol, TimeFrame.Month, last_month_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    barsM = api.get_bars(symbol, TimeFrame.Month, last_month_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # print('segundo else - sem last month bar')
                # barsM = api.get_bars(symbol, TimeFrame.Month, yesterday-td_month, yesterday, adjustment='raw' )
                barsM = api.get_bars(symbol, TimeFrame.Month, yesterday-td_month, adjustment='raw' )
        else:
            barsM = api.get_bars(symbol, TimeFrame.Month, start_date, end_date, adjustment='raw' )

        # Week
        if start_date == None:
            last_week_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Week').order_by('date').last()
            # print('Yesterday = ', yesterday)
            if last_week_bar_in_DB:
                # print('Last = ', last_week_bar_in_DB.date.date())
                if last_week_bar_in_DB.date.date() >= yesterday:
                    prev_week= last_week_bar_in_DB.date.date() - timedelta(weeks = 1)
                    # print('Previous week = ', prev_week)
                    # barsW = api.get_bars(symbol, TimeFrame.Week, prev_week, yesterday, adjustment='raw' )
                    barsW = api.get_bars(symbol, TimeFrame.Week, prev_week, adjustment='raw' )
                else:
                    # print('primeiro else - last week bar anterior ao yesterday')
                    # barsW = api.get_bars(symbol, TimeFrame.Week, last_week_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    barsW = api.get_bars(symbol, TimeFrame.Week, last_week_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # print('segundo else - sem last week bar')
                # barsW = api.get_bars(symbol, TimeFrame.Week, yesterday-td_week, yesterday, adjustment='raw' )
                barsW = api.get_bars(symbol, TimeFrame.Week, yesterday-td_week, adjustment='raw' )
        else:
            barsW = api.get_bars(symbol, TimeFrame.Week, start_date, end_date, adjustment='raw' )

        # Day
        if start_date == None:
            last_day_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Day').order_by('date').last()
            # print('Yesterday = ', yesterday)
            if last_day_bar_in_DB:
                # print('Last = ', last_day_bar_in_DB.date.date())
                if last_day_bar_in_DB.date.date() >= yesterday:
                    # print('entrei')
                    prev_day = last_day_bar_in_DB.date.date() - timedelta(days = 1)
                    # print('Previous Day = ', prev_day)
                    # barsD = api.get_bars(symbol, TimeFrame.Day, prev_day, yesterday, adjustment='raw' )
                    barsD = api.get_bars(symbol, TimeFrame.Day, prev_day, adjustment='raw' )
                else:
                    # print('primeiro else - last day bar anterior ao yesterday')
                    # barsD = api.get_bars(symbol, TimeFrame.Day, last_day_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    barsD = api.get_bars(symbol, TimeFrame.Day, last_day_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # print('segundo else - sem last day bar')
                # barsD = api.get_bars(symbol, TimeFrame.Day, yesterday-td_day, yesterday, adjustment='raw' )
                barsD = api.get_bars(symbol, TimeFrame.Day, yesterday-td_day, adjustment='raw' )
        else:
            # print('Else sem barras anteriores')
            barsD = api.get_bars(symbol, TimeFrame.Day, start_date, end_date, adjustment='raw' )

        # Hour
        if start_date == None:
            last_hour_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Hour').order_by('date').last()
            # print('Yesterday = ', yesterday)
            if last_hour_bar_in_DB:
                # print('Last = ', last_hour_bar_in_DB.date.date())
                if last_hour_bar_in_DB.date.date() >= yesterday:    # Checar se posso substituit yesterday por now
                    prev_hour= last_hour_bar_in_DB.date.date() - timedelta(days = 1)
                    # print('Previous Hour = ', prev_hour)
                    # barsH = api.get_bars(symbol, TimeFrame.Hour, prev_hour, yesterday, adjustment='raw' )
                    barsH = api.get_bars(symbol, TimeFrame.Hour, prev_hour, adjustment='raw' )
                else:
                    # barsH = api.get_bars(symbol, TimeFrame.Hour, last_hour_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    barsH = api.get_bars(symbol, TimeFrame.Hour, last_hour_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # barsH = api.get_bars(symbol, TimeFrame.Hour, yesterday-td_hour, yesterday, adjustment='raw' )
                barsH = api.get_bars(symbol, TimeFrame.Hour, yesterday-td_hour, adjustment='raw' )
        else:
            barsH = api.get_bars(symbol, TimeFrame.Hour, start_date, end_date, adjustment='raw' )

        # 5Minute
        if start_date == None:
            last_5minute_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='5Minute').order_by('date').last()
            # print('Yesterday = ', yesterday)
            if last_5minute_bar_in_DB:
                # print('Last = ', last_5minute_bar_in_DB.date.date())
                if last_5minute_bar_in_DB.date.date() >= yesterday:
                    prev_min= last_5minute_bar_in_DB.date.date()  - timedelta(days = 1)
                    # print('Previous Minute = ', prev_min)
                    # bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), prev_min, yesterday, adjustment='raw' )
                    bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), prev_min, adjustment='raw' )
                else:
                    # bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), last_5minute_bar_in_DB.date.date(), yesterday, adjustment='raw' )
                    bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), last_5minute_bar_in_DB.date.date(), adjustment='raw' )
            else:
                # print('segundo else - sem last 5Min bar')
                # bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), yesterday-td_minute, yesterday, adjustment='raw' )
                bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), yesterday-td_minute, adjustment='raw' )
        else:
            bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), start_date, end_date, adjustment='raw' )

    if bars:
        InsertBarsIntoDB(bars, timeframe)
    if barsM:
        InsertBarsIntoDB(barsM, 'Month')
    if barsW:
        InsertBarsIntoDB(barsW, 'Week')
    if barsD:
        InsertBarsIntoDB(barsD, 'Day')
    if barsH:
        InsertBarsIntoDB(barsH, 'Hour')
    if bars5Min:
        InsertBarsIntoDB(bars5Min, '5Minute')    

def UpdatePricesAlpaca(symbols, start_date=None, end_date=None, timeframe='ALL'):
    api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)    
    chunk_size = 200
    bars = barsM = barsW = barsD = barsH = bars5Min = None
    today=date.today()
    yesterday=date.today()-timedelta(1)
    td_month=timedelta(750)
    td_week=timedelta(200)
    td_day=timedelta(50)
    td_hour=timedelta(5)
    td_minute=timedelta(1)
    # print(timeframe)
    # print(symbols)
    for i in range(0, len(symbols), chunk_size):
        symbol_chunk = symbols[i:i+chunk_size]
        if timeframe == 'Month':
            bars = api.get_bars(symbol_chunk, TimeFrame.Month, yesterday-td_month, yesterday, adjustment='raw' )
        elif timeframe == 'Week':
            bars = api.get_bars(symbol_chunk, TimeFrame.Week, yesterday-td_week, yesterday, adjustment='raw' )
        elif timeframe == 'Day':
            bars = api.get_bars(symbol_chunk, TimeFrame.Day, yesterday-td_day, yesterday, adjustment='raw' )
        elif timeframe == 'Hour':
            bars = api.get_bars(symbol_chunk, TimeFrame.Hour, yesterday-td_hour, yesterday, adjustment='raw' )
        elif timeframe == '5Minute':
            bars = api.get_bars(symbol_chunk, TimeFrame(5, TimeFrameUnit.Minute), yesterday-td_minute, yesterday, adjustment='raw' )
        elif timeframe == 'ALL':
            barsM = api.get_bars(symbol_chunk, TimeFrame.Month, yesterday-td_month, yesterday, adjustment='raw' )
            barsW = api.get_bars(symbol_chunk, TimeFrame.Week, yesterday-td_week, yesterday, adjustment='raw' )
            barsD = api.get_bars(symbol_chunk, TimeFrame.Day, yesterday-td_day, yesterday, adjustment='raw' )
            barsH = api.get_bars(symbol_chunk, TimeFrame.Hour, yesterday-td_hour, yesterday, adjustment='raw' )
            bars5Min = api.get_bars(symbol_chunk, TimeFrame(5, TimeFrameUnit.Minute), yesterday-td_minute, yesterday, adjustment='raw' )

        if bars:
            InsertBarsIntoDB(bars, timeframe)
        if barsM:
            InsertBarsIntoDB(barsM, 'Month')
        if barsW:
            InsertBarsIntoDB(barsW, 'Week')
        if barsD:
            InsertBarsIntoDB(barsD, 'Day')
        if barsH:
            InsertBarsIntoDB(barsH, 'Hour')
        if bars5Min:
            InsertBarsIntoDB(bars5Min, '5Minute')


def WatchList(request, id=None):
    if request.POST:
        selecionadas = request.POST.getlist('selected[]')
        if selecionadas:
            for item in selecionadas:
                obj, created = watch_list.objects.update_or_create(
                    stock = stock.objects.get(id=item),
                    User = request.user,
                )
                # print(created)
    elif request.GET and id != None:
        pass
        # Chamar o mesmo form habilitando a MODAL
    lista = watch_list.objects.filter(User=request.user)
    # list_stocks = [item.stock.symbol for item in lista]
    # UpdatePricesAlpaca(list_stocks, timeframe='Day')
    for item in lista:
        UpdatePricesAlpacaOneStock([item.stock.symbol], timeframe='Day')
    context = {'watchlist':lista}
    return render(request, "cadastro/listas/watchlist.html", context)

def InserirWatchList(request):
    availableStocks=stock.objects.all()
    context = {'availableStocks':availableStocks}
    return render(request, "cadastro/listas/available_stocks.html", context)

def RemoverWatchList(request, pk):
    pass


def DashBoard(request):
    
    searchSymbol = None
    show_modal_stocks = False
    show_modal_watch = False
    lista_stocks = lista_stocks_filtered = stock.objects.all()

    if request.POST:
        selecionadas = request.POST.getlist('selected[]')
        acao = request.POST.get('acao')
        if selecionadas:
            if acao == 'Excluir':
                for item in selecionadas:
                    watch_list.objects.filter(stock=stock.objects.get(id=item), User = request.user).delete()
            elif acao == 'Incluir':
                for item in selecionadas:
                    obj, created = watch_list.objects.update_or_create(
                        stock = stock.objects.get(id=item),
                        User = request.user,
                    )
    elif request.GET.get('searchSymbol', None) != None:
        searchSymbol=request.GET.get('searchSymbol')
        lista_stocks_filtered = stock.objects.filter(symbol__contains=searchSymbol)
        show_modal_stocks = True
    
    dic_charts={}
    lista_watchlist = watch_list.objects.filter(User=request.user)
    for item in lista_watchlist:
        prices = stock_price.objects.filter(stock=item.stock.id, timeframe='Day')
        data=[go.Candlestick(x=[c.date for c in prices], open=[c.open for c in prices], 
            high=[c.high for c in prices], low=[c.low for c in prices], close=[c.close for c in prices])]
        layout=go.Layout(title=item.stock.symbol,
                xaxis_rangeslider_visible=False,
                autosize=False,
                width=400,
                height=300,
                margin=dict(l=5,r=5,b=5,t=50,pad=5)
                # yaxis_title = "Price (USD)", 
                # xaxis_title = "Date"
                )
        fig=go.Figure(data=data, layout=layout)
        fig.update_layout(title={'font_size': 15, 'xanchor': 'center', 'x': 0.5})
        chart = fig.to_html()
        dic_charts[item.id]=chart   

    context = {'dic_charts': dic_charts, 'watchlist': lista_watchlist, 'stocks': lista_stocks_filtered, 'show_modal_watch': show_modal_watch, 'show_modal_stocks': show_modal_stocks, 'titulo': 'DashBoard'}
    return render(request, "DashBoard.html", context)

def ShowGraph(request, stock_id=None, tf=None):
    if stock_id:
        stock_par=stock.objects.get(pk=stock_id)
        if request.POST:
            tf = request.POST.get('timeframe', None)
        if tf==None:
            tf='Day'
        UpdatePricesAlpacaOneStock([stock_par.symbol], timeframe=tf)  # Precisa ser uma lista, mesmo que unitária, para que a API responda como esperado
        prices = stock_price.objects.filter(stock=stock_par, timeframe=tf)

        # Calculando padrões
        for i in range(1, len(prices)):
            is_cross = 0
            is_cross = cross(prices, i, "ma20", "ma50") 
            if is_cross == 1:
                # print('Golden Cross', prices[i].date)
                obj, created = detected_patterns.objects.update_or_create(
                    stock_price = prices[i],
                    detected_pattern = 'Golden Cross ma20-ma50',
                    defaults={
                        'detection_method': 'SelfFunc'
                    },
                )
            elif is_cross == -1:
                # print('Death Cross', prices[i].date)
                obj, created = detected_patterns.objects.update_or_create(
                    stock_price = prices[i],
                    detected_pattern = 'Death Cross ma20-ma50',
                    defaults={
                        'detection_method': 'SelfFunc'
                    },
                )
            # else:
                # print('Sem cruzamento')
                

            if is_bullish_engulfing(prices, i):
                # print('{}It is a bullish engolfing'.format(prices[i].date))
                obj, created = detected_patterns.objects.update_or_create(
                    stock_price = prices[i],
                    detected_pattern = 'Bullish Engulfing',
                    defaults={
                        'detection_method': 'SelfFunc'
                    },
                )

            if is_bearish_engulfing(prices, i):
                # print('{}It is a bearish engolfing'.format(prices[i].date))
                obj, created = detected_patterns.objects.update_or_create(
                    stock_price = prices[i],
                    detected_pattern = 'Bearish Engulfing',
                    defaults={
                        'detection_method': 'SelfFunc'
                    },
                )


        figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing = 0)
        if tf == 'Hour' or tf == '5Minute':
            figure.add_trace(go.Candlestick(x=[c.date.strftime("%d/%m %H:%M") for c in prices], open=[c.open for c in prices], high=[c.high for c in prices], 
                low=[c.low for c in prices], close=[c.close for c in prices]), row=1, col=1)
            figure.add_trace(go.Scatter(x=[c.date.strftime("%d/%m %H:%M") for c in prices], y=[c.ma20 for c in prices], name = 'mm20',), row=1, col=1)
            figure.add_trace(go.Scatter(x=[c.date.strftime("%d/%m %H:%M") for c in prices], y=[c.ma50 for c in prices], name = 'mm50',), row=1, col=1)
            figure.add_trace(go.Scatter(x=[c.date.strftime("%d/%m %H:%M") for c in prices], y=[c.ma9 for c in prices], name = 'mm9',), row=1, col=1)
            figure.add_trace(go.Scatter(x=[c.date.strftime("%d/%m %H:%M") for c in prices], y=[c.ma200 for c in prices], name = 'mm200',), row=1, col=1)
            figure.add_trace(go.Bar(x=[c.date.strftime("%d/%m %H:%M") for c in prices], y=[c.volume for c in prices], showlegend=False, marker_color='#ef5350'), row=2, col=1)
            myshapes=[]
            for i in range(0,len(prices)):
                if detected_patterns.objects.filter(stock_price=prices[i]) and i != 0 and i != len(prices):
                    is_detected = detected_patterns.objects.filter(stock_price=prices[i])                    
                    for item in is_detected:
                        if item.detected_pattern == 'Bearish Engulfing':
                            myshapes.append(dict(type="rect", xref="x1", yref='y1', 
                                                x0=prices[i-1].date.strftime("%d/%m %H:%M"), x1=prices[i+1].date.strftime("%d/%m %H:%M"), 
                                                y0=float(prices[i].high)*1.01 , y1=float(prices[i].low)*0.99,
                                                opacity=0.4, fillcolor="red", line_color="red",))
                        if item.detected_pattern == 'Bullish Engulfing':
                            myshapes.append(dict(type="rect", xref="x1", yref='y1', 
                                                x0=prices[i-1].date.strftime("%d/%m %H:%M"), x1=prices[i+1].date.strftime("%d/%m %H:%M"), 
                                                y0=float(prices[i].high)*1.01 , y1=float(prices[i].low)*0.99,
                                                opacity=0.4, fillcolor="green", line_color="green",))
                        if item.detected_pattern == 'Golden Cross ma20-ma50':
                            myshapes.append(dict(type="circle", xref="x1", yref='y1', 
                                                x0=prices[i-1].date.strftime("%d/%m %H:%M"), x1=prices[i+1].date.strftime("%d/%m %H:%M"), 
                                                y0=float(prices[i].ma20)*1.01, y1=float(prices[i].ma20)*0.99,
                                                opacity=0.4, fillcolor="green", line_color="green",))
                        if item.detected_pattern == 'Death Cross ma20-ma50':
                            myshapes.append(dict(type="circle", xref="x1", yref='y1', 
                                                x0=prices[i-1].date.strftime("%d/%m %H:%M"), x1=prices[i+1].date.strftime("%d/%m %H:%M"), 
                                                y0=float(prices[i].ma20)*1.01, y1=float(prices[i].ma20)*0.99,
                                                opacity=0.4, fillcolor="red", line_color="red",))

        else:
            figure.add_trace(go.Candlestick(x=[c.date.date() for c in prices], open=[c.open for c in prices], high=[c.high for c in prices], 
                low=[c.low for c in prices], close=[c.close for c in prices]), row=1, col=1)
            figure.add_trace(go.Scatter(x=[c.date.date() for c in prices], y=[c.ma20 for c in prices], name = 'mm20',), row=1, col=1)
            figure.add_trace(go.Scatter(x=[c.date.date() for c in prices], y=[c.ma50 for c in prices], name = 'mm50',), row=1, col=1)
            figure.add_trace(go.Scatter(x=[c.date.date() for c in prices], y=[c.ma9 for c in prices], name = 'mm9',), row=1, col=1)
            figure.add_trace(go.Scatter(x=[c.date.date() for c in prices], y=[c.ma200 for c in prices], name = 'mm200',), row=1, col=1)
            figure.add_trace(go.Bar(x=[c.date.date() for c in prices], y=[c.volume for c in prices], showlegend=False, marker_color='#ef5350'), row=2, col=1)
            myshapes=[]
            for i in range(0,len(prices)):
                if detected_patterns.objects.filter(stock_price=prices[i]):
                    is_detected = detected_patterns.objects.filter(stock_price=prices[i])
                    for item in is_detected:
                        if item.detected_pattern == 'Bearish Engulfing':
                            myshapes.append(dict(type="rect", xref="x1", yref='y1', 
                                            x0=prices[i-1].date.date(), x1=prices[i+1].date.date(), 
                                            y0=float(prices[i].high)*1.05, y1=float(prices[i].low)*0.95,
                                            opacity=0.4, fillcolor="red", line_color="red",))
                        if item.detected_pattern == 'Bullish Engulfing':
                            myshapes.append(dict(type="rect", xref="x1", yref='y1', 
                                            x0=prices[i-1].date.date(), x1=prices[i+1].date.date(), 
                                            y0=float(prices[i].high)*1.05, y1=float(prices[i].low)*0.95,
                                            opacity=0.4, fillcolor="green", line_color="green",))
                        if item.detected_pattern == 'Golden Cross ma20-ma50':
                            myshapes.append(dict(type="circle", xref="x1", yref='y1', 
                                                x0=prices[i-1].date.date(), y0=float(prices[i].ma20)*1.02, 
                                                x1=prices[i+1].date.date(), y1=float(prices[i].ma20)*0.98,
                                                opacity=0.4, fillcolor="green", line_color="green",))
                        if item.detected_pattern == 'Death Cross ma20-ma50':
                            myshapes.append(dict(type="circle", xref="x1", yref='y1', 
                                                x0=prices[i-1].date.date(), y0=float(prices[i].ma20)*1.02, 
                                                x1=prices[i+1].date.date(), y1=float(prices[i].ma20)*0.98,
                                                opacity=0.4, fillcolor="red", line_color="red",))
        
        figure.update(layout_xaxis_rangeslider_visible=False)
        figure.update(layout_title=stock_par.symbol)
        figure.update(layout_autosize=False)
        figure.update(layout_width=1300)
        figure.update(layout_height=650)
        
        figure.update_yaxes(title="Price $", row=1, col=1, showgrid=True)
        figure.update_yaxes(title="Volume $", row=2, col=1, showgrid=False)
        figure.update_xaxes(type = "category", row=1)
        figure.update_xaxes(title_text='Date', type = "category", row=2, tickangle=65)
        
        figure.update_layout(title={'font_size': 22, 'xanchor': 'center', 'x': 0.5})

        figure.update_layout( shapes = myshapes )
        

        chart=figure.to_html()


    else:

        prices = []


    lista_watchlist = watch_list.objects.filter(User=request.user)
    lista_stocks = stock.objects.all()
    context = {'chart': chart, 'watchlist': lista_watchlist, 'stocks': lista_stocks, 'prices': prices, 'stock_id':stock_id, 'tf':tf, 'titulo': 'DashBoard'}
    return render(request, "DashBoard.html", context)



def twChart(request, exchange, stock):
    exchange = exchange
    stock = stock
    # print('passei')
    # print(exchange)
    # print(stock)
    context = {'exchange': exchange, 'stock':stock}
    return render(request, 'cadastro/modal/tw_chart_widget.html', context)

def findPatterns(pattern='ALL', assets=None, tf=None):
    if assets==None or tf==None:
        # print('Asset e Timeframe são obrigatórios')
        return
    else:
        for asset in assets:
            candles = stock_price.objects.filter(stock = asset.pk)
            if pattern=='ALL':
                # Bullish Engulfing
                for i in range(1, len(candles)):
                    # print(candles[i])
                    if is_bullish_engulfing(candles, i):
                        print('It is a bullish engulfing')