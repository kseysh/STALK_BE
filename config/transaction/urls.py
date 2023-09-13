from .views import *
from django.urls import path

urlpatterns = [
    path('data_to_sound/', data_to_sound, name='data_sound'),
    path('speech_to_text/', speech_to_text, name='speech_to_text'),
    path('user_info/', user_info, name='user_info'),
    path('buy/', buy, name='buy'),
    path('sell/', sell, name='sell'),
    path('like_stock/', like_stock, name='like_stock'),
    path('checkislike/',CheckIsLike.as_view()),
    path('stocklist/',StockAPIView.as_view()),
    path('createstockdatabase/',create_stock_database),
]