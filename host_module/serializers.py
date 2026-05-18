from rest_framework import serializers
from .models import TransactionsLoad, PostingsLog

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionsLoad
        fields = ['external_id', 'device_code', 'oper_date', 'amount', 'currency', 'card_number', 'status']

class PostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostingsLog
        fields = '__all__'