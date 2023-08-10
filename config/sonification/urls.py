from .views import *
from django.urls import path
from django.urls import re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

urlpatterns = [
    path('now_data/',now_data, name='now_data'),
    path('f_now_data/',f_now_data, name='f_now_data'),
    path('day_data/', day_data, name='day_data'),
    path('f_day_data/', f_day_data, name='f_day_data'),
    path('minute_data/', minute_data, name='minute_data'),
    path('week_data/', week_data, name='week_data'),
    path('f_week_data/', f_week_data, name='f_week_data'),
    path('data_to_sound/', data_to_sound, name='data_sound'),
    path('my_stocks/', my_stocks, name='my_stocks'),
    path('repeat_minute_data/', repeat_minute_data, name='repeat_minute_data'),
    path('buy/', buy, name='buy'),
    path('sell/', sell, name='sell'),
]