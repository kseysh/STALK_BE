from rest_framework import serializers
from .models import Stock, Record, UserStock

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['id']



class UserStockSerializer(serializers.ModelSerializer):
    stock = serializers.CharField(source='stock.name')
    stock_code = serializers.CharField(source='stock.symbol')
    user = serializers.CharField(source='user.user_nickname')

    class Meta:
        model = UserStock
        fields = '__all__'

class RecordSerializer(serializers.ModelSerializer):
    stock = serializers.CharField(source='stock.name')
    user = serializers.CharField(source='user.user_nickname')
    class Meta:
        model = Record
        fields = '__all__'