from django.db import models
from django.apps import apps
from accounts.models import User
# User = apps.get_model('accounts', 'User')

## 한유저가 좋아요 해논 stocks를 뽑아야하는데
class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100) 
    likes = models.IntegerField(default=0)
    liked_user = models.ManyToManyField(User, related_name="liked_stock", blank=True)
    is_domestic_stock = models.BooleanField(default=True)
    def __str__(self):
        return self.name

class UserStock(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    having_quantity = models.IntegerField()
    price = models.FloatField()
    profit_loss = models.FloatField()
    rate_profit_loss = models.FloatField()
    now_price = models.FloatField()
    def __str__(self):
        return f"{self.stock} - {self.user}"

class Record(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records', default=1)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE,default = 1)
    transaction_type = models.CharField(max_length=2) #구매 or 판매
    quantity = models.IntegerField()
    price = models.FloatField()
    left_money = models.FloatField()
    date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.stock} - {self.user}"
