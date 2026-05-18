from django.urls import path
from . import views

urlpatterns = [
    # Главная страница загрузки файлов
    path('', views.upload_page, name='upload'),
    
    # Страница со списком транзакций (заменили logs_page на transaction_logs)
    path('logs/', views.transaction_logs, name='transaction_logs'),
    
    # Страница сводных финансовых отчетов (убедись, что имя совпадает)
    path('reports/', views.financial_reports_view, name='financial_reports'),
]