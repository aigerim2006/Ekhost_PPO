from django.contrib import admin
# Импортируем измененные по ТЗ названия классов (с буквой s)
from .models import Terminal, MerchantAccount, ExchangeRate, TransactionsLoad, PostingsLog

@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ('device_code', 'merchant_id')
    search_fields = ('device_code', 'merchant_id')

@admin.register(MerchantAccount)
class MerchantAccountAdmin(admin.ModelAdmin):
    list_display = ('merchant_id', 'currency', 'account_number')
    list_filter = ('currency',)
    search_fields = ('merchant_id', 'account_number')

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('currency', 'rate', 'date')
    list_filter = ('currency', 'date')

@admin.register(TransactionsLoad)
class TransactionsLoadAdmin(admin.ModelAdmin):
    list_display = ('external_id', 'device_code', 'oper_date', 'amount', 'currency', 'status')
    list_filter = ('status', 'currency', 'oper_date')
    search_fields = ('external_id', 'device_code', 'card_number')

@admin.register(PostingsLog)
class PostingsLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant_id', 'account_number', 'amount_original', 'currency', 'sum_kgs_equiv', 'post_date', 'status')
    list_filter = ('status', 'currency', 'post_date')
    search_fields = ('merchant_id', 'account_number', 'transaction_ref')