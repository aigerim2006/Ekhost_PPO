from django.urls import path
from . import views
urlpatterns = [
    path('', views.upload_page, name='upload'),
    path('logs/', views.logs_page, name='logs'),
    path('reports/', views.reports_page, name='reports'),
    path('api/transactions/', views.transaction_list_api, name='api_transactions'),
    path('api/postings/', views.posting_list_api, name='api_postings'),
]
