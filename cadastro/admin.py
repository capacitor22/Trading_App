from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, stock, stock_price, detected_patterns, watch_list

admin.site.register(User, UserAdmin)
admin.site.register(stock)
admin.site.register(stock_price)
admin.site.register(detected_patterns)
admin.site.register(watch_list)