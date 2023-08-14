from rest_framework import serializers
from accounts.models import User    
from sonification.serializers import StockSerializer
class UserSerializer(serializers.ModelSerializer):
    liked_stock = StockSerializer(many=True)
    class Meta:
        model = User
        fields = ['id','username','user_nickname','user_property','user_email','user_property','liked_stock']
