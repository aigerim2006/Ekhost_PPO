from django.shortcuts import render, redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.files.storage import FileSystemStorage
from .services import process_excel_file, create_postings  
from .models import TransactionLoad, PostingLog
from .serializers import TransactionSerializer, PostingSerializer
from django.db.models import Sum, Count, Q, F
from .models import PostingLog
from django.db import models

def upload_page(request):
    if request.method == 'POST' and request.FILES.get('file'):
        myfile = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        process_excel_file(fs.path(filename))
        return redirect('logs')
    return render(request, 'host_module/upload.html')
def logs_page(request):
    # Получаем все транзакции, свежие сверху
    txs = TransactionLoad.objects.all().order_by('-load_date')
    return render(request, 'host_module/logs.html', {'transactions': txs})
@api_view(['GET'])
def transaction_list_api(request):
    """API для получения списка транзакций (JSON)"""
    transactions = TransactionLoad.objects.all()
    serializer = TransactionSerializer(transactions, many=True)
    return Response(serializer.data)
@api_view(['GET'])
def posting_list_api(request):
    """API для получения списка проводок (JSON)"""
    postings = PostingLog.objects.all()
    serializer = PostingSerializer(postings, many=True)
    return Response(serializer.data)
def reports_page(request):
    # 1. Получаем все проводки для верхней главной таблицы
    postings = PostingLog.objects.all().order_by('-post_date')

    # Ищем успешные проводки БЕЗ привязки к регистру (и Success, и success, и Выполнено)
    successful_postings = PostingLog.objects.all()

    # 2. Группировка по Мерчантам (добавили явный order_by() для сброса системных сортировок)
    merchant_report = successful_postings.values('merchant_id').annotate(
        total_amount=Sum('amount_kgs')
    ).order_by('-total_amount')

    # 3. Группировка по расчетным счетам с подменой имени для шаблона
    device_report = successful_postings.values('account_number').annotate(
        device_code=F('account_number'),
        total_ops=Count('id'),
        total_sum=Sum('amount_kgs')
    ).order_by('-total_sum')

    # 4. Общий объем успешных списаний
    total_day_sum = successful_postings.aggregate(Sum('amount_kgs'))['amount_kgs__sum'] or 0

    context = {
        'postings': postings,
        'merchant_report': merchant_report,
        'device_report': device_report,
        'total_day_sum': total_day_sum,
    }
    
    return render(request, 'host_module/reports.html', context)