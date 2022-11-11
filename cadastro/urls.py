from django.urls import path, reverse_lazy
from .views import InserirWatchList, WatchList, AlpacaShowAccount, ImportStocksAlpaca, UpdatePricesAlpaca, ListStocks, ListPrices
from django.contrib.auth import views as auth_views

app_name = "cadastro"

urlpatterns = [
    path('', AlpacaShowAccount, name='PainelInicial'),
    path('ShowAccount', AlpacaShowAccount, name='ShowAccount'),
    path('ListStocks', ListStocks.as_view(), name='ListStocks'),
    path('ImportStocksAlpaca', ImportStocksAlpaca, name='ImportStocksAlpaca'),
    path('ImportStocksAlpaca', ImportStocksAlpaca, name='ImportStocksAlpaca'),
    path('watchlist', WatchList, name='watchlist'),
    path('InserirWatchList', InserirWatchList, name='InserirWatchList'),
    path('ListPrices/<int:pk>/', ListPrices, name='ListPrices'),
    
    path('login/', auth_views.LoginView.as_view(template_name='acesso/usermanagement/form-login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='acesso/usermanagement/login.html', success_url=reverse_lazy('acesso:PainelInicial')), name='password_change'),
    path('password_change-done/', auth_views.PasswordChangeDoneView.as_view(template_name='acesso/usermanagement/password_change_feita.html'), name='password_change_done'),
    path('password_reset/', 
        auth_views.PasswordResetView.as_view(template_name='acesso/usermanagement/login.html', 
        email_template_name='acesso/usermanagement/password_reset_email.html',
        success_url=reverse_lazy('acesso:password_reset_done')), 
        name='password_reset'),
    path('password_reset_done/', 
        auth_views.PasswordResetDoneView.as_view(template_name='acesso/usermanagement/password_reset_email_enviado.html'), 
        name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(template_name='acesso/usermanagement/login.html', 
        success_url=reverse_lazy('acesso:password_reset_complete')), 
        name='password_reset_confirm'),
    path('password_reset_complete/', 
        auth_views.PasswordResetCompleteView.as_view(template_name='acesso/usermanagement/password_reset_complete.html'), 
        name='password_reset_complete'),


]