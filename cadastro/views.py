from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.list import ListView
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame, URL
import requests, json
from datetime import datetime

from config import *
from django.shortcuts import redirect
from django.urls import reverse_lazy


from django.shortcuts import render
from .models import stock, stock_price, watch_list

ACCOUNT_URL = "{}/v2/account".format(BASE_URL)
ORDERS_URL = "{}/v2/orders".format(BASE_URL)
POSITIONS_URL = "{}/v2/positions".format(BASE_URL)
ASSETS_URL = "{}/v2/assets".format(BASE_URL)
HEADERS = {'APCA-API-KEY-ID':API_KEY, 'APCA-API-SECRET-KEY':SECRET_KEY}


def AlpacaShowAccount(request):
    account = requests.get(ACCOUNT_URL, headers=HEADERS)
    # OBS: account é um dicionário mas os outros são listas de dicionarios, entao precisa adaptar
    if account:
        accout_json = account.json()
        print('Accounts:')
        print(accout_json) 
        print('Keys:')
        print(accout_json.keys()) 
    orders = requests.get(ORDERS_URL, headers=HEADERS)
    if orders:
        orders_json = orders.json()
        print('Orders:')
        print(orders_json) 
        # print('Keys:')
        # print(orders_json.keys()) 
    positions = requests.get(POSITIONS_URL, headers=HEADERS)
    if positions:
        positions_json = positions.json()
        print('Positions:')
        print(positions_json) 
        # print('Keys:')
        # print(positions_json.keys()) 
    # assets = requests.get(ASSETS_URL, headers=HEADERS)
    # if assets:
    #     assets_json = assets.json()
    #     print('Assets:')
    #     print(assets_json) 
    #     print('Keys:')
    #     print(assets_json.keys()) 

    context = {'account': accout_json, 'orders': orders_json, 'positions':positions_json}
    return render(request, "form.html", context)

class ListStocks(LoginRequiredMixin, ListView):
    # login_url = reverse_lazy('acesso:login')
    model = stock
    template_name = 'cadastro/listas/stocks.html'

def WatchList(request):
    if request.POST:
        selecionadas = request.POST.getlist('selected[]')
        if selecionadas:
            for item in selecionadas:
                obj, created = watch_list.objects.update_or_create(
                    stock = stock.objects.get(id=item),
                    User = request.user,
                )
                print(created)
    lista = watch_list.objects.filter(User=request.user)
    context = {'watchlist':lista}
    return render(request, "cadastro/listas/watchlist.html", context)

def InserirWatchList(request):
    availableStocks=stock.objects.all()
    context = {'availableStocks':availableStocks}
    return render(request, "cadastro/listas/available_stocks.html", context)

def ImportStocksAlpaca(request):
    api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)
    assets = api.list_assets()
    processed = active_and_tradable = imported = updated = 0

    for asset in assets:
        processed += 1
        if asset.status == 'active' and asset.tradable:
            active_and_tradable += 1
            # print('class_alpaca = ', asset.class)
            # print('min_order_size = ', asset.min_order_size)
            # print('min_trade_increment = ', asset.min_trade_increment)
            # print('price_increment = ', asset.price_increment)

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


def UpdatePricesAlpaca(request, symbols, start_date, end_date, timeframe):
    api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)
    
    chunk_size = 200
    for i in range(0, len(symbols), chunk_size):
        symbol_chunk = symbols[i:i+chunk_size]
        if timeframe == 'TimeFrame.Month':
            bars = api.get_bars(symbol_chunk, TimeFrame.Month, start_date, end_date, adjustment='raw' )
        elif timeframe == 'TimeFrame.Week':
            bars = api.get_bars(symbol_chunk, TimeFrame.Week, start_date, end_date, adjustment='raw' )
        elif timeframe == 'TimeFrame.Day':
            bars = api.get_bars(symbol_chunk, TimeFrame.Day, start_date, end_date, adjustment='raw' )
        elif timeframe == 'TimeFrame.Hour':
            bars = api.get_bars(symbol_chunk, TimeFrame.Hour, start_date, end_date, adjustment='raw' )
        elif timeframe == 'TimeFrame.Minute':
            bars = api.get_bars(symbol_chunk, TimeFrame.Minute, start_date, end_date, adjustment='raw' )

        for symbol in bars:
            print('Processing symbol ', symbol)
            for bar in bars[symbol]:
                print(bar.t,bar.o,bar.h,bar.l,bar.c,bar.v)
                # Inserir na tabela de cotações
                # obj, created = stock_price.objects.update_or_create(
                #     stock = stock.objects.get(symbol=symbol),
                #     timeframe = timeframe,
                #     date = bar.t,
                #     defaults={
                #         'origin': 'Alpaca',
                #         # 'class_alpaca': asset.class,
                #         'easy_to_borrow': asset.easy_to_borrow,
                #         'exchange': asset.exchange,
                #     },
                # )
    
    return bars

def UpdatePricesAlpaca_bkp(request, symbols, start_date, end_date, timeframe):
    api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL)
    
    # # considerando que receberia um parametro symbols com todos os simbolos que quero atualizar:
    # chunk_size = 200
    
    # for i in range(0, len(symbols), chunk_size):
    #     symbol_chunk = symbols[i:i+chunk_size]
    #     # Efetuar a consulta acima (ninho de ifs) para todo o symbol_chunk

    #     for symbol in bars:
    #         print('Processing symbol ', symbol)
    #         for bar in bars[symbol]:
    #             # Inserir na tabela de cotações

    if timeframe == 'TimeFrame.Month':
        bars = api.get_bars([symbols], TimeFrame.Month, start_date, end_date, adjustment='raw' )
    elif timeframe == 'TimeFrame.Week':
        bars = api.get_bars([symbols], TimeFrame.Week, start_date, end_date, adjustment='raw' )
    elif timeframe == 'TimeFrame.Day':
        bars = api.get_bars([symbols], TimeFrame.Day, start_date, end_date, adjustment='raw' )
    elif timeframe == 'TimeFrame.Hour':
        bars = api.get_bars([symbols], TimeFrame.Hour, start_date, end_date, adjustment='raw' )
    elif timeframe == 'TimeFrame.Minute':
        bars = api.get_bars([symbols], TimeFrame.Minute, start_date, end_date, adjustment='raw' )


    
    for bar in bars:
        print(bar.t,bar.o,bar.h,bar.l,bar.c,bar.v)
        # processed += 1
        # if asset.status == 'active' and asset.tradable:
        #     active_and_tradable += 1
        #     obj, created = stock.objects.update_or_create(
        #         id_alpaca = asset.id,
        #         defaults={
        #             'origin': 'Alpaca',
        #             # 'class_alpaca': asset.class,
        #             'easy_to_borrow': asset.easy_to_borrow,
        #             'exchange': asset.exchange,
        #         },
        #     )
        #     if created:
        #         imported += 1
    
    return bars

def ListPrices(request, pk):
    stock_obj = stock.objects.get(id=pk)
    if request.POST:
        start_date = request.POST.get('startdate', None)
        end_date = request.POST.get('enddate', None)
        timeframe = request.POST.get('timeframe', None)
        if (start_date != None) and (end_date != None) and (timeframe != None):
            UpdatePricesAlpaca(request, [stock_obj.symbol], start_date, end_date, timeframe)
    prices = stock_price.objects.filter(stock = pk)
    context = {'prices':prices, 'stock': stock_obj}
    return render(request, "cadastro/listas/prices.html", context)
