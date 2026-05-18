from django.db import models

class Terminal(models.Model):
    device_code = models.CharField("Код устройства", max_length=50, unique=True)
    merchant_id = models.IntegerField("ID Мерчанта")

    class Meta:
        verbose_name = "Терминал"
        verbose_name_plural = "1. Справочник терминалов"

    def __str__(self):
        return f"Терминал {self.device_code} (Мерчант {self.merchant_id})"


class MerchantAccount(models.Model):
    merchant_id = models.IntegerField("ID Мерчанта")
    currency = models.CharField("Валюта счета", max_length=3) # KGS, USD, EUR, KZT
    account_number = models.CharField("Номер расчетного счета", max_length=20)

    class Meta:
        verbose_name = "Счет мерчанта"
        verbose_name_plural = "2. Расчетные счета мерчантов"
        # Жесткая защита базы данных от дублирования счетов в одинаковой валюте
        unique_together = ('merchant_id', 'currency')

    def __str__(self):
        return f"Мерчант {self.merchant_id} | {self.currency} -> {self.account_number}"


class TransactionLoad(models.Model):
    external_id = models.CharField("Внешний ID транзакции", max_length=100, unique=True)
    device_code = models.CharField("Код устройства", max_length=50)
    oper_date = models.DateTimeField("Дата и время операции")
    amount = models.DecimalField("Сумма", max_digits=15, decimal_places=2)
    currency = models.CharField("Валюта", max_length=3)
    card_number = models.CharField("Номер карты (маскированный)", max_length=20)
    status = models.CharField("Статус обработки", max_length=50, default='New')
    load_date = models.DateTimeField("Дата импорта файла", auto_now_add=True)

    class Meta:
        verbose_name = "Загруженная транзакция"
        verbose_name_plural = "3. Буфер транзакций МПЦ"

    def __str__(self):
        return f"Транзакция {self.external_id} [{self.status}]"


class PostingLog(models.Model):
    merchant_id = models.IntegerField("ID Мерчанта")
    account_number = models.CharField("Номер счета зачисления", max_length=50)
    amount_original = models.DecimalField("Сумма в валюте операции", max_digits=12, decimal_places=2)
    currency = models.CharField("Оригинальная валюта", max_length=3)
    amount_kgs = models.DecimalField("Сумма проводки (KGS)", max_digits=12, decimal_places=2)
    post_date = models.DateTimeField("Дата формирования проводки", auto_now_add=True)
    status = models.CharField("Статус АБС", max_length=20, default='Success')

    class Meta:
        verbose_name = "Проводка в АБС"
        verbose_name_plural = "4. Реестр проводок в АБС"

    def __str__(self):
        return f"Проводка #{self.id} | Мерчант {self.merchant_id} -> {self.amount_kgs} KGS"