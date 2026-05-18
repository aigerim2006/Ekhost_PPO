from django.db import models
from django.utils import timezone

# 1. Terminals
class Terminal(models.Model):
    device_code = models.CharField("Device Code", max_length=50, unique=True)
    merchant_id = models.IntegerField("Merchant ID")

    class Meta:
        verbose_name = "Терминал"
        verbose_name_plural = "1. Terminals (Справочник устройств)"

    def __str__(self):
        return f"{self.device_code} (Мерчант {self.merchant_id})"


# 2. Merchant_Account
class MerchantAccount(models.Model):
    merchant_id = models.IntegerField("Merchant ID")
    currency = models.CharField("Currency", max_length=3) # KGS, USD, EUR, KZT
    account_number = models.CharField("Account Number", max_length=20)

    class Meta:
        verbose_name = "Счет мерчанта"
        verbose_name_plural = "2. Merchant Accounts (Счета мерчантов)"
        unique_together = ('merchant_id', 'currency')

    def __str__(self):
        return f"Мерчант {self.merchant_id} [{self.currency}] -> {self.account_number}"


# 3. Exchange_Rate
class ExchangeRate(models.Model):
    currency = models.CharField("Currency", max_length=3)
    rate = models.DecimalField("Rate", max_digits=10, decimal_places=4)
    date = models.DateField("Date")

    class Meta:
        verbose_name = "Курс валюты"
        verbose_name_plural = "3. Exchange Rates (Курсы НБКР)"
        unique_together = ('currency', 'date')

    def __str__(self):
        return f"{self.currency} на {self.date} = {self.rate} KGS"


# 4. Transactions_Load
class TransactionsLoad(models.Model):
    external_id = models.CharField("External ID", max_length=100, unique=True)
    device_code = models.CharField("Device Code", max_length=50)
    oper_date = models.DateTimeField("Oper Date Time")
    amount = models.DecimalField("Amount", max_digits=15, decimal_places=2)
    currency = models.CharField("Currency", max_length=3)
    card_number = models.CharField("Card Number", max_length=20)
    status = models.CharField("Status", max_length=50, default='New') # New, Processed, Completed, Failed
    load_date = models.DateTimeField("Load Date", auto_now_add=True)

    class Meta:
        verbose_name = "Транзакция буфера"
        verbose_name_plural = "4. Transactions Load (Буфер МПЦ)"

    def __str__(self):
        return f"Tx {self.external_id} ({self.status})"


# 5. Postings_Log
class PostingsLog(models.Model):
    transaction_ref = models.CharField("Transaction Ref", max_length=100)
    merchant_id = models.IntegerField("Merchant ID")
    account_number = models.CharField("Account Number", max_length=50)
    amount_original = models.DecimalField("Amount Original", max_digits=15, decimal_places=2)
    currency = models.CharField("Currency", max_length=3)
    sum_kgs_equiv = models.DecimalField("Sum KGS Equiv", max_digits=15, decimal_places=2)
    # ИЗМЕНЕНО: Заменили auto_now_add=True на default=timezone.now, чтобы фиксировать дату из файла
    post_date = models.DateTimeField("Post Date", default=timezone.now)
    status = models.CharField("Status", max_length=20, default='PENDING')

    class Meta:
        verbose_name = "Проводка в АБС"
        verbose_name_plural = "5. Postings Log (Реестр АБС)"

    def __str__(self):
        return f"Posting {self.id} -> {self.sum_kgs_equiv} KGS ({self.status})"