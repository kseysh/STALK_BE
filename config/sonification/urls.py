from .views import *
from django.urls import path
from django.urls import re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

urlpatterns = [
    path('now_data/',now_data, name='now_data'),
    path('il_bong/', il_bong, name='il_bong'),
    path('boon_bong/', boon_bong, name='boon_bong'),
    path('data_to_sound/', data_to_sound, name='data_sound'),
    path('my_stocks/', my_stocks, name='my_stocks'),
    path('buy/', buy, name='buy'),
    path('sell/', sell, name='sell'),
]