import openpyxl
import requests
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate

from .models import Terminal, MerchantAccount, ExchangeRate, TransactionsLoad, PostingsLog

def get_nbkr_rate(currency, date_target=None):
    """Получение курса на конкретную дату транзакции"""
    if currency == 'KGS':
        return Decimal('1.0')
    
    if date_target:
        local_rate = ExchangeRate.objects.filter(currency=currency, date=date_target).first()
        if local_rate:
            return local_rate.rate

    try:
        url = 'https://www.nbkr.kg/XML/daily.xml'
        response = requests.get(url, timeout=3)
        root = ET.fromstring(response.content)
        for cur in root.findall('Currency'):
            if cur.get('ISOCode') == currency:
                val = Decimal(cur.find('Value').text.replace(',', '.'))
                if date_target:
                    ExchangeRate.objects.get_or_create(currency=currency, date=date_target, defaults={'rate': val})
                return val
    except:
        pass
    
    rates = {'USD': Decimal('89.43'), 'EUR': Decimal('96.10'), 'KZT': Decimal('0.20')}
    return rates.get(currency, Decimal('1.0'))


def upload_page(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            sheet = wb.active
        except Exception as e:
            return render(request, 'host_module/upload.html', {'error': f'Не удалось прочитать Excel-файл: {e}'})
        
        success_count = 0
        duplicate_count = 0
        
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or row[0] is None:
                continue
                
            try:
                ext_id = str(row[0]).strip()
                dev_code = str(row[1]).strip()
                oper_date_raw = row[2]
                currency = str(row[3]).strip()
                amount_raw = row[4]
                card_num = str(row[5] or '').strip()
                
                if TransactionsLoad.objects.filter(external_id=ext_id).exists():
                    duplicate_count += 1
                    continue

                terminal_exists = Terminal.objects.filter(device_code=dev_code).exists()
                initial_status = 'New' if terminal_exists else 'Error: Unknown Device'

                if len(card_num) >= 12:
                    masked_card = f"{card_num[:4]}********{card_num[-4:]}"
                else:
                    masked_card = card_num if card_num else "0000********0000"

                # ИСПРАВЛЕНО: Умный разбор даты, поддерживающий форматы как с секундами, так и без них
                if isinstance(oper_date_raw, str):
                    oper_date_str = oper_date_raw.strip()
                    parsed_date = None
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
                        try:
                            parsed_date = datetime.strptime(oper_date_str, fmt)
                            break
                        except ValueError:
                            continue
                    oper_date = parsed_date if parsed_date else datetime.now()
                else:
                    if oper_date_raw:
                        if hasattr(oper_date_raw, 'tzinfo') and oper_date_raw.tzinfo is not None:
                            oper_date = oper_date_raw.replace(tzinfo=None)
                        else:
                            oper_date = oper_date_raw
                    else:
                        oper_date = datetime.now()

                clean_amount = str(amount_raw or '0').replace(',', '.').replace(' ', '')
                amount_decimal = Decimal(clean_amount)

                TransactionsLoad.objects.create(
                    external_id=ext_id,
                    device_code=dev_code,
                    oper_date=oper_date,
                    amount=amount_decimal,
                    currency=currency,
                    card_number=masked_card,
                    status=initial_status
                )
                success_count += 1

            except Exception as e:
                return render(request, 'host_module/upload.html', {
                    'error': f'Критическая ошибка в строке №{row_idx}: {e}.'
                })
            
        return redirect('transaction_logs')

    return render(request, 'host_module/upload.html')


def transaction_logs(request):
    # Читаем дату из календаря (GET-запрос)
    f_date = request.GET.get('filter_date')

    if request.method == 'POST' and 'create_postings' in request.POST:
        new_txs = TransactionsLoad.objects.filter(status='New')
        
        grouped_data = new_txs.annotate(op_date_only=TruncDate('oper_date')).values('device_code', 'currency', 'op_date_only').annotate(total_amnt=Sum('amount'))
        
        for group in grouped_data:
            d_code = group['device_code']
            curr = group['currency']
            aggregated_amount = group['total_amnt']
            tx_date = group['op_date_only']
            
            terminal = Terminal.objects.filter(device_code=d_code).first()
            if not terminal:
                continue
                
            m_id = terminal.merchant_id
            merchant_acc = MerchantAccount.objects.filter(merchant_id=m_id, currency=curr).first()
            rate = get_nbkr_rate(curr, date_target=tx_date)
            amount_kgs = aggregated_amount * rate
            
            naive_post_date = datetime.combine(tx_date, datetime.min.time())

            if merchant_acc:
                PostingsLog.objects.create(
                    transaction_ref=f"Реестр терминала {d_code}",
                    merchant_id=m_id,
                    account_number=merchant_acc.account_number,
                    amount_original=aggregated_amount,
                    currency=curr,
                    sum_kgs_equiv=amount_kgs,
                    post_date=naive_post_date,
                    status="Success"
                )
                new_txs.filter(device_code=d_code, currency=curr, oper_date__date=tx_date).update(status='Completed')
            else:
                PostingsLog.objects.create(
                    transaction_ref=f"Ошибка: нет счета {d_code}",
                    merchant_id=m_id,
                    account_number="MISSING",
                    amount_original=aggregated_amount,
                    currency=curr,
                    sum_kgs_equiv=0,
                    post_date=naive_post_date,
                    status="Failed"
                )
                new_txs.filter(device_code=d_code, currency=curr, oper_date__date=tx_date).update(status='Failed')
                
        return redirect('financial_reports')

    # ИСПРАВЛЕНО: Фильтрация записей на странице по выбранной из календаря дате
    transactions = TransactionsLoad.objects.all()
    if f_date:
        transactions = transactions.filter(oper_date__date=f_date)
        
    transactions = transactions.order_by('-oper_date')
    return render(request, 'host_module/transaction_logs.html', {
        'transactions': transactions,
        'v_date': f_date
    })


def financial_reports_view(request):
    postings = PostingsLog.objects.all()
    
    distinct_dates = PostingsLog.objects.annotate(d=TruncDate('post_date')).values_list('d', flat=True).distinct().order_by('-d')
    distinct_terminals = Terminal.objects.all().order_by('device_code')
    distinct_currencies = ['KGS', 'USD', 'EUR', 'KZT']

    f_date = request.GET.get('filter_date')
    f_terminal = request.GET.get('filter_terminal')
    f_currency = request.GET.get('filter_currency')
    
    period = request.GET.get('period', 'all')
    period_title = "за всё время"

    if f_date:
        postings = postings.filter(post_date__date=f_date)
        period_title = f"за дату {f_date}"
    elif period != 'all':
        now = datetime.now()
        if period == 'day':
            postings = postings.filter(post_date__date=now.date())
            period_title = "за сегодня"
        elif period == 'week':
            postings = postings.filter(post_date__gte=now - timedelta(days=7))
            period_title = "за неделю"
        elif period == 'month':
            postings = postings.filter(post_date__gte=now - timedelta(days=30))
            period_title = "за месяц"

    if f_terminal:
        postings = postings.filter(transaction_ref__contains=f_terminal)

    if f_currency:
        postings = postings.filter(currency=f_currency)

    merchant_summary = postings.filter(status='Success').values('merchant_id').annotate(total_sum=Sum('sum_kgs_equiv')).order_by('-total_sum')
    account_summary = postings.filter(status='Success').values('account_number', 'currency').annotate(tx_count=Count('id'), total_sum=Sum('sum_kgs_equiv')).order_by('-total_sum')
    grand_total_kgs = postings.filter(status='Success').aggregate(total=Sum('sum_kgs_equiv'))['total'] or Decimal('0.00')

    error_transactions = TransactionsLoad.objects.filter(status__startswith='Error')
    if f_date:
        error_transactions = error_transactions.filter(oper_date__date=f_date)
    if f_terminal:
        error_transactions = error_transactions.filter(device_code=f_terminal)
    if f_currency:
        error_transactions = error_transactions.filter(currency=f_currency)

    context = {
        'postings': postings.order_by('-post_date'),
        'merchant_summary': merchant_summary,
        'account_summary': account_summary,
        'grand_total_kgs': grand_total_kgs,
        'error_transactions': error_transactions,
        'period': period,
        'period_title': period_title,
        'distinct_dates': distinct_dates,
        'distinct_terminals': distinct_terminals,
        'distinct_currencies': distinct_currencies,
        'v_date': f_date,
        'v_terminal': f_terminal,
        'v_currency': f_currency
    }
    return render(request, 'host_module/financial_reports.html', context)