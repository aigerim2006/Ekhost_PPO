from django.db import models
class Terminal(models.Model):
    device_code = models.CharField("Код устройства", max_length=50, unique=True)
    merchant_id = models.IntegerField("ID Мерчанта")
class MerchantAccount(models.Model):
    merchant_id = models.IntegerField()
    currency = models.CharField(max_length=3) # KGS, USD...
    account_number = models.CharField(max_length=20)
class TransactionLoad(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    device_code = models.CharField(max_length=50)
    oper_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    card_number = models.CharField(max_length=20)
    status = models.CharField(max_length=50, default='New')
    load_date = models.DateTimeField(auto_now_add=True)
class PostingLog(models.Model):
    # Убедись, что имена полей СТРОГО такие:
    merchant_id = models.IntegerField("ID Мерчанта")
    account_number = models.CharField(max_length=50)
    amount_original = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    amount_kgs = models.DecimalField(max_digits=12, decimal_places=2)
    post_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Success')

    def __str__(self):
        return f"Posting {self.merchant_id} - {self.amount_kgs} KGS"
