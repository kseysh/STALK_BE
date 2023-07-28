from .views import *
from django.urls import path

urlpatterns = [
    path('now_data/',now_data, name='now_data'),
    path('il_bong/', il_bong, name='il_bong'),
    path('data_to_sound/', data_to_sound, name='data_sound')
]