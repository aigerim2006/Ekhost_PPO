from django.contrib import admin
from .models import Terminal, MerchantAccount, TransactionLoad, PostingLog

@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ('device_code', 'merchant_id')

@admin.register(MerchantAccount)
class MerchantAccountAdmin(admin.ModelAdmin):
    list_display = ('merchant_id', 'currency', 'account_number')

@admin.register(TransactionLoad)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('external_id', 'device_code', 'currency', 'amount', 'status', 'load_date')
    list_filter = ('status', 'currency')

@admin.register(PostingLog)
class PostingAdmin(admin.ModelAdmin):
    # Исправленные названия колонок (теперь они совпадают с models.py)
    list_display = ('merchant_id', 'account_number', 'amount_original', 'currency', 'amount_kgs', 'post_date', 'status')
    list_filter = ('status', 'currency', 'merchant_id')
    