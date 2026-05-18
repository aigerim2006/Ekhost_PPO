import openpyxl
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from django.utils import timezone  # Добавлено для работы со временем
from .models import TransactionLoad, Terminal, MerchantAccount, PostingLog

def get_nbkr_rate(currency, date=None):
    """Автоматическое получение курса с сайта НБКР"""
    if currency == 'KGS':
        return Decimal('1.0')
    try:
        response = requests.get('https://www.nbkr.kg/XML/daily.xml', timeout=5)
        root = ET.fromstring(response.content)
        for cur in root.findall('Currency'):
            if cur.get('ISOCode') == currency:
                return Decimal(cur.find('Value').text.replace(',', '.'))
    except:
        pass
    # Если сайт недоступен, используем средний курс
    rates = {'USD': Decimal('89.43'), 'EUR': Decimal('96.10'), 'KZT': Decimal('0.20')}
    return rates.get(currency, Decimal('1.0'))

def mask_card(card_number):
    """Маскирование карты: 4111********4444"""
    card_str = str(card_number)
    if len(card_str) >= 12:
        return f"{card_str[:4]}********{card_str[-4:]}"
    return card_str

def process_excel_file(file_path):
    """Загрузка данных из Excel в БД"""
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        ext_id, dev_code, op_date, curr, amnt, card = row
        
        if not ext_id: continue # Пропуск пустых строк
        
        if TransactionLoad.objects.filter(external_id=str(ext_id)).exists():
            continue
            
        status = "Processed"
        if not Terminal.objects.filter(device_code=str(dev_code)).exists():
            status = "Error: Unknown Device"
            
        # Убираем RuntimeWarning: делаем дату "осознанной" (aware)
        if isinstance(op_date, datetime):
            if timezone.is_naive(op_date):
                op_date = timezone.make_aware(op_date)
        else:
            op_date = timezone.now()

        TransactionLoad.objects.create(
            external_id=str(ext_id),
            device_code=str(dev_code),
            oper_date=op_date,
            currency=str(curr),
            amount=Decimal(str(amnt)),
            card_number=mask_card(card),
            status=status
        )

def create_postings():
    """Бизнес-логика: Агрегация и формирование проводок"""
    # Исправлено: берем и Processed, и Failed транзакции для возможности исправления ошибок
    transactions = TransactionLoad.objects.filter(status__in=["Processed", "Failed"])
    
    for tx in transactions:
        term = None
        try:
            term = Terminal.objects.get(device_code=tx.device_code)
            account = MerchantAccount.objects.get(
                merchant_id=term.merchant_id, 
                currency=tx.currency
            )
            
            rate = get_nbkr_rate(tx.currency)
            amount_kgs = tx.amount * rate
            
            PostingLog.objects.create(
                merchant_id=term.merchant_id,         
                account_number=account.account_number,
                amount_original=tx.amount,             
                currency=tx.currency,                  
                amount_kgs=amount_kgs,                
                status="Success"
            )
            
            tx.status = "Completed"
            tx.save()

        except Terminal.DoesNotExist:
            tx.status = "Error: Terminal Not Found"
            tx.save()
            
        except MerchantAccount.DoesNotExist:
            m_id = term.merchant_id if term else 0
            # Чтобы не плодить дубликаты записей MISSING при повторных нажатиях:
            if tx.status != "Failed":
                PostingLog.objects.create(
                    merchant_id=m_id,
                    account_number="MISSING",
                    amount_original=tx.amount,
                    currency=tx.currency,
                    amount_kgs=0,
                    status=f"Error: No {tx.currency} account"
                )
            tx.status = "Failed"
            tx.save()