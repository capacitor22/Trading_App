from alpaca_trade_api.rest import TimeFrame, URL
from datetime import date, timedelta
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

from config import *
from .models import stock, stock_price, watch_list
from .forms import CustomCriaUsuarioForm
from.utils import get_plot

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


def UpdatePricesAlpaca(symbols, start_date=None, end_date=None, timeframe='ALL'):

    def InsertBarsIntoDB(new_bars, new_timeframe):
        for bar in new_bars:
            # print(bar.S, bar.t, bar.o, bar.h, bar.l, bar.c, bar.v)
            obj, created = stock_price.objects.update_or_create(
                stock = stock.objects.get(symbol=bar.S),
                timeframe = new_timeframe,
                date = bar.t,
                defaults={
                    'open': float(bar.o), 
                    'high': float(bar.h), 
                    'low': float(bar.l), 
                    'close': float(bar.c), 
                    'volume': float(bar.v)
                },
            )


    api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)    
    chunk_size = 200
    bars = barsM = barsW = barsD = barsH = barsMin = None
    today=date.today()
    yesterday=date.today()-timedelta(1)
    td_month=timedelta(750)
    td_week=timedelta(200)
    td_day=timedelta(50)
    td_hour=timedelta(5)
    td_minute=timedelta(1)
    for i in range(0, len(symbols), chunk_size):
        symbol_chunk = symbols[i:i+chunk_size]
        # print('symbolos: ', symbol_chunk)
        if timeframe == 'Month':
            bars = api.get_bars(symbol_chunk, TimeFrame.Month, start_date, end_date, adjustment='raw' )
        elif timeframe == 'Week':
            bars = api.get_bars(symbol_chunk, TimeFrame.Week, start_date, end_date, adjustment='raw' )
        elif timeframe == 'Day':
            bars = api.get_bars(symbol_chunk, TimeFrame.Day, start_date, end_date, adjustment='raw' )
        elif timeframe == 'Hour':
            bars = api.get_bars(symbol_chunk, TimeFrame.Hour, start_date, end_date, adjustment='raw' )
        elif timeframe == 'Minute':
            bars = api.get_bars(symbol_chunk, TimeFrame.Minute, start_date, end_date, adjustment='raw' )
        elif timeframe == 'ALL':
            barsM = api.get_bars(symbol_chunk, TimeFrame.Month, yesterday-td_month, yesterday, adjustment='raw' )
            barsW = api.get_bars(symbol_chunk, TimeFrame.Week, yesterday-td_week, yesterday, adjustment='raw' )
            barsD = api.get_bars(symbol_chunk, TimeFrame.Day, yesterday-td_day, yesterday, adjustment='raw' )
            barsH = api.get_bars(symbol_chunk, TimeFrame.Hour, yesterday-td_hour, yesterday, adjustment='raw' )
            barsMin = api.get_bars(symbol_chunk, TimeFrame.Minute, yesterday-td_minute, yesterday, adjustment='raw' )

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
        if barsMin:
            InsertBarsIntoDB(barsMin, 'Minute')


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
    # Desabilitando temporariamente para nao demorar o refresh
    # UpdatePricesAlpaca(list_stocks, 'ALL')
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
    dic_charts={}
    lista_watchlist = watch_list.objects.filter(User=request.user)
    for item in lista_watchlist:
        prices = stock_price.objects.filter(stock=item.stock.id, timeframe='Day')
        data=[go.Candlestick(x=[c.date for c in prices], open=[c.open for c in prices], 
            high=[c.high for c in prices], low=[c.low for c in prices], close=[c.close for c in prices])]
        layout=go.Layout(title=item.stock.symbol,
                xaxis_rangeslider_visible=False,
                yaxis_title = "Price (USD)", 
                xaxis_title = "Date"
                )
        fig=go.Figure(data=data, layout=layout)
        fig.update_layout(title={'font_size': 22, 'xanchor': 'center', 'x': 0.5})
        chart = fig.to_html()
        dic_charts[item.id]=chart
    
    lista_stocks = stock.objects.all()

    context = {'dic_charts': dic_charts, 'watchlist': lista_watchlist, 'stocks': lista_stocks, 'titulo': 'DashBoard'}
    return render(request, "DashBoard.html", context)

def ShowGraph(request, stock_id=None, tf=None):
    if stock_id:
        stock_par=stock.objects.get(pk=stock_id)
        if tf==None:
            tf='Day'
        prices = stock_price.objects.filter(stock=stock_par, timeframe=tf)
        # Usando PLOTLY 
        data=[go.Candlestick(x=[c.date for c in prices], open=[c.open for c in prices], 
            high=[c.high for c in prices], low=[c.low for c in prices], close=[c.close for c in prices])]
        layout=go.Layout(title=stock_par.symbol,
                xaxis_rangeslider_visible=False,
                yaxis_title = "Price (USD)", 
                xaxis_type = "category",
                xaxis_title = "Date"
                )
        fig=go.Figure(data=data, layout=layout)
        
        fig.update_layout(title={'font_size': 22, 'xanchor': 'center', 'x': 0.5})
        chart=fig.to_html()
    else:
        prices = []

    lista_watchlist = watch_list.objects.filter(User=request.user)
    lista_stocks = stock.objects.all()
    context = {'chart': chart, 'watchlist': lista_watchlist, 'stocks': lista_stocks, 'prices': prices, 'titulo': 'DashBoard'}
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