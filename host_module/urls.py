from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_page, name='upload'),
    path('logs/', views.transaction_logs, name='transaction_logs'),
    path('reports/', views.financial_reports_view, name='financial_reports'),
]