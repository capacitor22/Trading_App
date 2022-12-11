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
import requests, json
import tulipy as ti
import numpy as np

from config import *
from .models import stock, stock_price, watch_list
from .forms import CustomCriaUsuarioForm
from .utils import get_plot, is_bullish_engulfing, is_bearish_engulfing

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
            return redirect(reverse_lazy("acesso:PainelInicial"))

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
        print('Symbol = {} - Timeframe = {} - DateTime = {}', bar.S, new_timeframe, bar.t)
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
    bars = barsM = barsW = barsD = barsH = barsMin = None
    today=date.today()
    yesterday=date.today()-timedelta(1)
    last_month=date.today()-timedelta(weeks=5)
    last_week=date.today()-timedelta(weeks=1)
    last_hour=date.today()-timedelta(hours=1)
    last_minute=date.today()-timedelta(minutes=1)
    print('last_month',last_month)
    print('last_week',last_week)
    print('last_hour',last_hour)
    print('last_minute',last_minute)
    td_month=timedelta(weeks = 900)
    td_week=timedelta(weeks = 201)
    td_day=timedelta(days = 260) # Descontando os FDS
    td_hour=timedelta(hours = 250)
    td_minute=timedelta(days = 2)

    # td_month=timedelta(750)
    # td_week=timedelta(200)
    # td_day=timedelta(50)
    # td_hour=timedelta(5)
    # td_minute=timedelta(1)

    thisStock = stock.objects.get(symbol=symbol[0])
    
    if start_date == None:
        if timeframe == 'Month':
            last_month_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Month').order_by('date').last()
            if last_month_bar_in_DB:
                bars = api.get_bars(symbol, TimeFrame.Month, last_month_bar_in_DB.date, end_date, adjustment='raw' )
            else:
                bars = api.get_bars(symbol, TimeFrame.Month, start_date, end_date, adjustment='raw' )
        elif timeframe == 'Week':
            # Week
            last_week_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Week').order_by('date').last()
            if last_week_bar_in_DB:
                bars = api.get_bars(symbol, TimeFrame.Week, last_week_bar_in_DB.date, yesterday, adjustment='raw' )
            else:
                barsW = api.get_bars(symbol, TimeFrame.Week, yesterday-td_week, yesterday, adjustment='raw' )
        elif timeframe == 'Day':
            # Day
            last_day_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Day').order_by('date').last()
            if last_day_bar_in_DB:
                bars = api.get_bars(symbol, TimeFrame.Day, last_day_bar_in_DB.date, yesterday, adjustment='raw' )
            else:
                barsD = api.get_bars(symbol, TimeFrame.Day, yesterday-td_day, yesterday, adjustment='raw' )
        elif timeframe == 'Hour':
            # Hour
            last_hour_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Hour').order_by('date').last()
            if last_hour_bar_in_DB:
                bars = api.get_bars(symbol, TimeFrame.Hour, last_hour_bar_in_DB.date, yesterday, adjustment='raw' )
            else:
                barsH = api.get_bars(symbol, TimeFrame.Hour, yesterday-td_hour, yesterday, adjustment='raw' )
        elif timeframe == '5Minute':
            # 5Minute
            last_minute_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Minute').order_by('date').last()
            if last_minute_bar_in_DB:
                bars = api.get_bars(symbol, TimeFrame.Minute, last_minute_bar_in_DB.date, yesterday, adjustment='raw' )
            else:
                barsMin = api.get_bars(symbol, TimeFrame.Minute, yesterday-td_minute, yesterday, adjustment='raw' )
        
        
        elif timeframe == 'ALL':

            # # Month
            # print('month')
            # last_month_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Month').order_by('date').last()
            # print('Yesterday = ', yesterday)
            # if last_month_bar_in_DB:
            #     print('Last = ', last_month_bar_in_DB.date.date())
            #     # barsM = api.get_bars(symbol, TimeFrame.Month, last_month_bar_in_DB.date.date(), yesterday, adjustment='raw' )
            #     if last_month_bar_in_DB.date.date() >= yesterday:
            #         prev_month= last_month_bar_in_DB.date.date() - timedelta(weeks = 4)
            #         print('Previous month = ', prev_month)
            #         barsM = api.get_bars(symbol, TimeFrame.Month, prev_month, yesterday, adjustment='raw' )
            #     else:
            #         print('primeiro else - last month bar anterior ao yesterday')
            #         barsM = api.get_bars(symbol, TimeFrame.Month, last_month_bar_in_DB.date.date(), yesterday, adjustment='raw' )
            # else:
            #     print('segundo else - sem last month bar')
            #     print('Inicio = ', yesterday - td_month)
            #     barsM = api.get_bars(symbol, TimeFrame.Month, yesterday-td_month, yesterday, adjustment='raw' )

            # # Week
            # print('Week')
            # last_week_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Week').order_by('date').last()
            # print('Yesterday = ', yesterday)
            # if last_week_bar_in_DB:
            #     print('Last = ', last_week_bar_in_DB.date.date())
            #     # barsW = api.get_bars(symbol, TimeFrame.Week, last_week_bar_in_DB.date.date(), yesterday, adjustment='raw' )
            #     if last_week_bar_in_DB.date.date() >= yesterday:
            #         prev_week= last_week_bar_in_DB.date.date() - timedelta(weeks = 1)
            #         print('Previous week = ', prev_week)
            #         barsW = api.get_bars(symbol, TimeFrame.Week, prev_week, yesterday, adjustment='raw' )
            #     else:
            #         print('primeiro else - last week bar anterior ao yesterday')
            #         barsW = api.get_bars(symbol, TimeFrame.Week, last_week_bar_in_DB.date.date(), yesterday, adjustment='raw' )
            # else:
            #     print('segundo else - sem last week bar')
            #     print('Inicio = ', yesterday - td_week)
            #     barsW = api.get_bars(symbol, TimeFrame.Week, yesterday-td_week, yesterday, adjustment='raw' )

            # # Day
            # print('Day')
            # last_day_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Day').order_by('date').last()
            # print('Yesterday = ', yesterday)
            # if last_day_bar_in_DB:
            #     print('Last = ', last_day_bar_in_DB.date.date())
            #     if last_day_bar_in_DB.date.date() >= yesterday:
            #         prev_day = last_day_bar_in_DB.date.date() - timedelta(days = 1)
            #         print('Previous Day = ', prev_day)
            #         barsD = api.get_bars(symbol, TimeFrame.Day, prev_day, yesterday, adjustment='raw' )
            #     else:
            #         print('primeiro else - last day bar anterior ao yesterday')
            #         barsD = api.get_bars(symbol, TimeFrame.Day, last_day_bar_in_DB.date.date(), yesterday, adjustment='raw' )
            # else:
            #     print('segundo else - sem last day bar')
            #     print('Inicio = ', yesterday - td_day)
            #     barsD = api.get_bars(symbol, TimeFrame.Day, yesterday-td_day, yesterday, adjustment='raw' )

            # # Hour
            # print('Hour')            
            # last_hour_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='Hour').order_by('date').last()
            # print('Yesterday = ', yesterday)
            # if last_hour_bar_in_DB:
            #     print('Last = ', last_hour_bar_in_DB.date.date())
            #     if last_hour_bar_in_DB.date.date() >= yesterday:    # Checar se posso substituit yesterday por now
            #         prev_hour= last_hour_bar_in_DB.date.date() - timedelta(days = 1)
            #         print('Previous Hour = ', prev_hour)
            #         # barsH = api.get_bars(symbol, TimeFrame.Hour, prev_hour, today - timedelta(hours = 1), adjustment='raw' )
            #         barsH = api.get_bars(symbol, TimeFrame.Hour, prev_hour, yesterday, adjustment='raw' )
            #     else:
            #         barsH = api.get_bars(symbol, TimeFrame.Hour, last_hour_bar_in_DB.date.date(), yesterday, adjustment='raw' )
            # else:
            #     barsH = api.get_bars(symbol, TimeFrame.Hour, yesterday-td_hour, yesterday, adjustment='raw' )
            
            # 5Minute
            print('5Minute')
            last_5minute_bar_in_DB = stock_price.objects.filter(stock=thisStock, timeframe='5Minute').order_by('date').last()
            print('Yesterday = ', yesterday)
            if last_5minute_bar_in_DB:
                print('Last = ', last_minute_bar_in_DB.date.date())
                if last_5minute_bar_in_DB.date.date() >= yesterday:
                    prev_min= last_5minute_bar_in_DB.date.date()  - timedelta(days = 1)
                    print('Previous Minute = ', prev_min)
                    # barsMin = api.get_bars(symbol, TimeFrame.Minute, prev_min, yesterday, adjustment='raw' )
                    bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), prev_min, yesterday, adjustment='raw' )
                else:
                    bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), last_5minute_bar_in_DB.date.date(), yesterday, adjustment='raw' )
            else:
                print('segundo else - sem last 5Min bar')
                print('Inicio = ', yesterday - td_minute)
                bars5Min = api.get_bars(symbol, TimeFrame(5, TimeFrameUnit.Minute), yesterday-td_minute, yesterday, adjustment='raw' )
                # print('BARS:')
                # print(bars5Min)
    # if bars:
    #     InsertBarsIntoDB(bars, timeframe)
    # if barsM:
    #     InsertBarsIntoDB(barsM, 'Month')
    # if barsW:
    #     InsertBarsIntoDB(barsW, 'Week')
    # if barsD:
    #     InsertBarsIntoDB(barsD, 'Day')
    # if barsH:
    #     InsertBarsIntoDB(barsH, 'Hour')
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
    for i in range(0, len(symbols), chunk_size):
        symbol_chunk = symbols[i:i+chunk_size]
        if timeframe == 'Month':
            bars = api.get_bars(symbol_chunk, TimeFrame.Month, start_date, end_date, adjustment='raw' )
        elif timeframe == 'Week':
            bars = api.get_bars(symbol_chunk, TimeFrame.Week, start_date, end_date, adjustment='raw' )
        elif timeframe == 'Day':
            bars = api.get_bars(symbol_chunk, TimeFrame.Day, start_date, end_date, adjustment='raw' )
        elif timeframe == 'Hour':
            bars = api.get_bars(symbol_chunk, TimeFrame.Hour, start_date, end_date, adjustment='raw' )
        elif timeframe == '5Minute':
            bars = api.get_bars(symbol_chunk, TimeFrame(5, TimeFrameUnit.Minute), start_date, end_date, adjustment='raw' )
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
                print(created)
    elif request.GET and id != None:
        pass
        # Chamar o mesmo form habilitando a MODAL
    lista = watch_list.objects.filter(User=request.user)
    list_stocks = [item.stock.symbol for item in lista]
    # Desabilitar se não quiser a atualizacao dos preços sempre que entrar na watchlist
    UpdatePricesAlpaca(list_stocks, 'Day')
    context = {'watchlist':lista}
    return render(request, "cadastro/listas/watchlist.html", context)

def InserirWatchList(request):
    availableStocks=stock.objects.all()
    context = {'availableStocks':availableStocks}
    return render(request, "cadastro/listas/available_stocks.html", context)

def RemoverWatchList(request, pk):
    pass

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
    print('processed = ', processed)
    print('active_and_tradable = ', active_and_tradable)
    print('imported = ', imported)
    print('updated = ', updated)
    return redirect(reverse_lazy("cadastro:ListStocks"))

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
        UpdatePricesAlpacaOneStock([stock_par.symbol])  # Precisa ser uma lista, mesmo que unitária, para que a API responda como esperado
        if tf==None:
            tf='Day'
        prices = stock_price.objects.filter(stock=stock_par, timeframe=tf)
        # Usando PLOTLY 
        data=[go.Candlestick(x=[c.date for c in prices], open=[c.open for c in prices], high=[c.high for c in prices], low=[c.low for c in prices], close=[c.close for c in prices]),
            go.Line(x=[c.date for c in prices], y=[c.ma200 for c in prices],),
            go.Line(x=[c.date for c in prices], y=[c.ma50 for c in prices],),
            go.Line(x=[c.date for c in prices], y=[c.ma20 for c in prices],),
            go.Line(x=[c.date for c in prices], y=[c.ma9 for c in prices],),
            ]
        layout=go.Layout(title=stock_par.symbol,
                xaxis_rangeslider_visible=False,                
                autosize=False,
                width=1000,
                height=700,
                # margin=dict(l=5,r=5,b=5,t=50,pad=5)                
                yaxis_title = "Price (USD)", 
                xaxis_type = "category",
                xaxis_title = "Date"
                )
        fig=go.Figure(data=data, layout=layout)
        
        fig.update_layout(title={'font_size': 22, 'xanchor': 'center', 'x': 0.5})
        chart=fig.to_html()
    else:
        prices = []

    if request.POST:
        # UpdatePricesAlpaca([stock_par.symbol])
        # UpdatePricesAlpacaOneStock([stock_par.symbol])  # Precisa ser uma lista, mesmo que unitária, para que a API responda como esperado
        for i in range(1, len(prices)):
            if is_bullish_engulfing(prices, i):
                print('{}It is a bullish engolfing'.format(prices[i].date))
            if is_bearish_engulfing(prices, i):
                print('{}It is a bearish engolfing'.format(prices[i].date))

    lista_watchlist = watch_list.objects.filter(User=request.user)
    lista_stocks = stock.objects.all()
    context = {'chart': chart, 'watchlist': lista_watchlist, 'stocks': lista_stocks, 'prices': prices, 'stock_id':stock_id, 'tf':tf, 'titulo': 'DashBoard'}
    return render(request, "DashBoard.html", context)


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

def twChart(request, exchange, stock):
    exchange = exchange
    stock = stock
    print('passei')
    print(exchange)
    print(stock)
    context = {'exchange': exchange, 'stock':stock}
    return render(request, 'cadastro/modal/tw_chart_widget.html', context)

def findPatterns(pattern='ALL', assets=None, tf=None):
    if assets==None or tf==None:
        print('Asset e Timeframe são obrigatórios')
        return
    else:
        for asset in assets:
            candles = stock_price.objects.filter(stock = asset.pk)
            if pattern=='ALL':
                # Bullish Engulfing
                for i in range(1, len(candles)):
                    print(candles[i])
                    if is_bullish_engulfing(candles, i):
                        print('It is a bullish engulfing')