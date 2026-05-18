from django.shortcuts import render, redirect
from django.contrib import messages
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum, Count, F

from .services import process_excel_file, create_postings  
from .models import TransactionLoad, PostingLog
from .serializers import TransactionSerializer, PostingSerializer

def upload_page(request):
    if request.method == 'POST' and request.FILES.get('file'):
        myfile = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        process_excel_file(fs.path(filename))
        messages.success(request, "Файл успешно загружен в буфер системы!")
        return redirect('logs')
    return render(request, 'host_module/upload.html')

def logs_page(request):
    txs = TransactionLoad.objects.all().order_by('-load_date')
    return render(request, 'host_module/logs.html', {'transactions': txs})

def reports_page(request):
    # ИСПРАВЛЕНО: Ловим клик по желтой кнопке "Сформировать проводки (АБС)"
    if request.GET.get('generate') == 'true':
        # Проверяем, есть ли транзакции, готовые к проведению (новые или ранее упавшие)
        to_process = TransactionLoad.objects.filter(status__in=["Processed", "Failed"]).count()
        
        if to_process > 0:
            create_postings()
            # Проверяем, остались ли после обработки ошибки из-за счетов
            has_errors = TransactionLoad.objects.filter(status="Failed").exists()
            if has_errors:
                messages.warning(request, "Проводки сформированы, но часть транзакций упала в ошибку (проверьте счета мерчантов в админке).")
            else:
                messages.success(request, f"Успешно обработано транзакций: {to_process} шт. Все проводки переданы в АБС!")
        else:
            messages.info(request, "Нет новых транзакций для обработки. Загрузите свежий файл.")
        
        return redirect('reports')

    # 1. Получаем все проводки для верхней таблицы истории
    postings = PostingLog.objects.all().order_by('-post_date')

    # 2. Фильтруем ТОЛЬКО успешные проводки для финансовой аналитики и сводок
    successful_postings = PostingLog.objects.filter(status__iexact='Success')

    # Группировка по Мерчантам
    merchant_report = successful_postings.values('merchant_id').annotate(
        total_amount=Sum('amount_kgs')
    ).order_by('-total_amount')

    # Группировка по Валютным расчетным счетам (как требует ТЗ банка)
    device_report = successful_postings.values('account_number').annotate(
        device_code=F('account_number'),
        total_ops=Count('id'),
        total_sum=Sum('amount_kgs')
    ).order_by('-total_sum')

    # Общий объем списаний по банку в сомовом эквиваленте
    total_day_sum = successful_postings.aggregate(Sum('amount_kgs'))['amount_kgs__sum'] or 0

    context = {
        'postings': postings,
        'merchant_report': merchant_report,
        'device_report': device_report,
        'total_day_sum': total_day_sum,
    }
    
    return render(request, 'host_module/reports.html', context)

# --- rest_framework API views ---
@api_view(['GET'])
def transaction_list_api(request):
    transactions = TransactionLoad.objects.all()
    serializer = TransactionSerializer(transactions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def posting_list_api(request):
    postings = PostingLog.objects.all()
    serializer = PostingSerializer(postings, many=True)
    return Response(serializer.data)