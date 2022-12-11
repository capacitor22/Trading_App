from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime as dt

class User(AbstractUser):
    pass

class stock (models.Model):
    origin = models.CharField(max_length=30, null=True, blank=True)
    class_alpaca = models.CharField(max_length=100, null=True, blank=True)
    easy_to_borrow = models.CharField(max_length=5, null=True, blank=True)
    exchange = models.CharField(max_length=100, null=True, blank=True)
    fractionable = models.CharField(max_length=5, null=True, blank=True)
    id_alpaca = models.CharField(max_length=100, null=True, blank=True)
    maintenance_margin_requirement = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    marginable = models.CharField(max_length=5, null=True, blank=True)
    min_order_size = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    min_trade_increment = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True) 
    price_increment = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    shortable = models.CharField(max_length=5, null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)
    symbol = models.CharField(max_length=20, null=True, blank=True)
    tradable = models.CharField(max_length=5, null=True, blank=True)
    def __str__(self):
        return self.symbol + ' - ' + self.name
    class Meta:
        ordering = ['symbol'] 

class stock_price(models.Model):
    stock = models.ForeignKey(stock, on_delete=models.CASCADE)
    timeframe = models.CharField(max_length=10, null=True, blank=True)
    date = models.DateTimeField()
    open = models.DecimalField(max_digits=15, decimal_places=5)
    high = models.DecimalField(max_digits=15, decimal_places=5)
    low = models.DecimalField(max_digits=15, decimal_places=5)
    close = models.DecimalField(max_digits=15, decimal_places=5)
    adjusted_close = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    volume = models.DecimalField(max_digits=15, decimal_places=5)
    ma9 = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    ma20 = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    ma50 = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    ma200 = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    bbh = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    bbmm = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    bbl = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    def __str__(self):
        return self.stock.symbol + ' - ' + self.timeframe + ' - ' + self.date.strftime("%d-%m-%Y %H:%M:%S")

class watch_list(models.Model):
    User = models.ForeignKey(User, on_delete=models.CASCADE)
    stock = models.ForeignKey(stock, on_delete=models.CASCADE)

    def __str__(self):
        return self.stock.symbol + ' - ' + self.stock.name
    