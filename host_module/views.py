import openpyxl
from decimal import Decimal
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta

from .models import Terminal, MerchantAccount, ExchangeRate, TransactionsLoad, PostingsLog

# ==========================================
# 1. СТРАНИЦА ЗАГРУЗКИ И ПАРСИНГА EXCEL
# ==========================================
def upload_page(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        
        try:
            # Читаем только значения формул/ячеек
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            sheet = wb.active
        except Exception as e:
            return render(request, 'host_module/upload.html', {'error': f'Не удалось прочитать Excel-файл: {e}'})
        
        success_count = 0
        duplicate_count = 0
        
        # Начинаем со 2-й строки, чтобы пропустить заголовки (ID, DeviceCode, OperDateTime...)
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or row[0] is None:
                continue
                
            try:
                # Извлекаем данные по позициям
                ext_id = str(row[0]).strip()
                dev_code = str(row[1]).strip()
                oper_date_raw = row[2]
                currency = str(row[3]).strip()
                amount_raw = row[4]
                card_num = str(row[5] or '').strip()
                
                # Исключение №2: Защита от дубликатов из ТЗ
                if TransactionsLoad.objects.filter(external_id=ext_id).exists():
                    duplicate_count += 1
                    continue

                # Исключение №1: Проверка существования терминала в справочнике банка
                terminal_exists = Terminal.objects.filter(device_code=dev_code).exists()
                initial_status = 'New' if terminal_exists else 'Error: Unknown Device'

                # Автоматическое маскирование карты ради безопасности (PCI DSS)
                if len(card_num) >= 12:
                    masked_card = f"{card_num[:4]}********{card_num[-4:]}"
                else:
                    masked_card = card_num if card_num else "0000********0000"

                # Обработка даты и времени операции
                if isinstance(oper_date_raw, str):
                    try:
                        oper_date = timezone.datetime.strptime(oper_date_raw, "%Y-%m-%d %H:%M:%S")
                        oper_date = timezone.make_aware(oper_date)
                    except ValueError:
                        oper_date = timezone.now()
                else:
                    if oper_date_raw and timezone.is_naive(oper_date_raw):
                        oper_date = timezone.make_aware(oper_date_raw)
                    else:
                        oper_date = oper_date_raw or timezone.now()

                # Безопасное приведение суммы к Decimal
                clean_amount = str(amount_raw or '0').replace(',', '.').replace(' ', '')
                amount_decimal = Decimal(clean_amount)

                # Записываем транзакцию в первичный буфер МПЦ
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
                    'error': f'Критическая ошибка в строке №{row_idx}: {e}. Проверьте структуру данных.'
                })
            
        if success_count > 0:
            return redirect('transaction_logs')
        else:
            return render(request, 'host_module/upload.html', {
                'error': f'Файл обработан, но транзакции не добавлены. Обнаружено дубликатов: {duplicate_count}.'
            })

    return render(request, 'host_module/upload.html')


# ==========================================
# 2. РЕЕСТР ТРАНЗАКЦИЙ И ФОРМИРОВАНИЕ ПРОВОДОК
# ==========================================
def transaction_logs(request):
    # Если бухгалтер нажал кнопку "Сформировать проводки (АБС)"
    if request.method == 'POST' and 'create_postings' in request.POST:
        # Берем все новые транзакции из буфера
        new_txs = TransactionsLoad.objects.filter(status='New')
        
        # Группируем по DeviceCode и Валюте для агрегации по ТЗ
        grouped_data = new_txs.values('device_code', 'currency').annotate(total_amnt=Sum('amount'))
        
        for group in grouped_data:
            d_code = group['device_code']
            curr = group['currency']
            aggregated_amount = group['total_amnt']
            
            terminal = Terminal.objects.filter(device_code=d_code).first()
            if not terminal:
                continue
                
            m_id = terminal.merchant_id
            
            # Маппинг счетов
            merchant_acc = MerchantAccount.objects.filter(merchant_id=m_id, currency=curr).first()
            
            if merchant_acc:
                account_number = merchant_acc.account_number
                posting_status = 'SUCCESS'
            else:
                account_number = "НЕ НАЙДЕН СЧЕТ"
                posting_status = 'FAILED'

            # Конвертация валюты
            if curr == 'KGS':
                rate = Decimal('1.0000')
            else:
                rate_obj = ExchangeRate.objects.filter(currency=curr).order_by('-date').first()
                rate = rate_obj.rate if rate_obj else Decimal('1.0000')

            sum_kgs = aggregated_amount * rate

            # Пишем проводку в реестр АБС
            PostingsLog.objects.create(
                transaction_ref=f"Пакет по устройству {d_code} за {timezone.now().date()}",
                merchant_id=m_id,
                account_number=account_number,
                amount_original=aggregated_amount,
                currency=curr,
                sum_kgs_equiv=sum_kgs,
                status=posting_status
            )
            
        # Помечаем транзакции как обработанные
        new_txs.filter(status='New').update(status='Processed')
        return redirect('transaction_logs')

    # Отображение всех транзакций в реестре
    transactions = TransactionsLoad.objects.all().order_by('-oper_date')
    return render(request, 'host_module/transaction_logs.html', {'transactions': transactions})


# ==========================================
# 3. ФИНАНСОВЫЕ ОТЧЕТЫ И СВОДНЫЕ ТАБЛИЦЫ
# ==========================================
def financial_reports_view(request):
    period = request.GET.get('period', 'day')
    now = timezone.now()
    
    if period == 'week':
        start_date = now - timedelta(days=7)
        period_title = "за последние 7 дней"
    elif period == 'month':
        start_date = now - timedelta(days=30)
        period_title = "за последние 30 дней"
    else:
        start_date = now - timedelta(days=1)
        period_title = "за текущие сутки"

    # Фильтруем успешные проводки за период
    postings = PostingsLog.objects.filter(post_date__gte=start_date).order_by('-post_date')
    success_postings = postings.filter(status='SUCCESS')

    # Оборот по торговым точкам (Мерчантам)
    merchant_summary = success_postings.values('merchant_id').annotate(
        total_sum=Sum('sum_kgs_equiv')
    ).order_by('-total_sum')

    # Распределение по внутренним расчетным счетам
    account_summary = success_postings.values('account_number', 'currency').annotate(
        tx_count=Count('id'),
        total_sum=Sum('sum_kgs_equiv')
    ).order_by('-total_sum')

    # Общий суммарный объем списаний в KGS
    grand_total_kgs = success_postings.aggregate(total=Sum('sum_kgs_equiv'))['total'] or Decimal('0.00')

    # Реестр необработанных транзакций (Ошибки)
    error_transactions = TransactionsLoad.objects.filter(
        status__startswith='Error'
    ).order_by('-oper_date')

    context = {
        'postings': postings,
        'merchant_summary': merchant_summary,
        'account_summary': account_summary,
        'grand_total_kgs': grand_total_kgs,
        'error_transactions': error_transactions,
        'period': period,
        'period_title': period_title,
    }
    return render(request, 'host_module/financial_reports.html', context)