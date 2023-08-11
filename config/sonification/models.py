from django.db import models
from accounts.models import User

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100) 
    likes = models.IntegerField()
    def __str__(self):
        return self.name

class UserStock(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    having_quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    profit_loss = models.DecimalField(max_digits=10, decimal_places=2)
    rate_profit_loss = models.DecimalField(max_digits=10, decimal_places=2)
    now_price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"{self.stock} - {self.user}"

class Record(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records', default=1)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE,default = 1)
    transaction_type = models.CharField(max_length=2) #구매 or 판매
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    left_money = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.stock} - {self.user}"
