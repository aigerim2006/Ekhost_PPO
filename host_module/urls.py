from django.urls import path
from . import views

urlpatterns = [
    # Страница загрузки (главная)
    path('', views.upload_page, name='upload'),
    
    # Лог транзакций
    path('logs/', views.logs_page, name='logs'),
    
    # Финансовые отчеты и проводки
    path('reports/', views.reports_page, name='reports'),
    
    # API эндпоинты (для rest_framework)
    path('api/transactions/', views.transaction_list_api, name='api_transactions'),
    path('api/postings/', views.posting_list_api, name='api_postings'),
]