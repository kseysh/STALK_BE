from django.urls import path
from . import views

urlpatterns = [
    path('newslist/', views.get_realtime_news),
    path('detail/', views.get_specific_news),
    path('stockcode/', views.get_news_by_stock_code),
]