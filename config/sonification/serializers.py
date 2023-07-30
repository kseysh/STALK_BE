from rest_framework import serializers
from .models import Stock, Record, UserStock

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['symbol', 'name']

class UserStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStock
        fields = '__all__'

class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Record
        fields = '__all__'