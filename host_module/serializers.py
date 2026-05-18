from rest_framework import serializers
from .models import TransactionLoad, PostingLog
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionLoad
        # Указываем, какие поля мы хотим отдавать по API
        fields = ['external_id', 'device_code', 'oper_date', 'amount', 'currency', 'card_number', 'status']
class PostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostingLog
        fields = '__all__'
