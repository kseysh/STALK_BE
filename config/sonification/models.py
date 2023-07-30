from django.db import models


class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100) 

class User(models.Model):
    name = models.CharField(max_length=15,unique=True)
    money = models.IntegerField()
    # stocks = models.ManyToManyField(Stock, through='UserStock', related_name='users', blank=True)

class UserStock(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    having_quantity = models.IntegerField()
    price = models.IntegerField()
    profit_loss = models.IntegerField()

class Record(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records', default=1)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE,default = 1)
    transaction_type = models.CharField(max_length=2) #구매 or 판매
    quantity = models.IntegerField()
    price = models.IntegerField()
    left_money = models.IntegerField()
    date = models.DateField(auto_now_add=True)
