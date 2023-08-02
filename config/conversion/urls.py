from .views import *
from django.urls import path

urlpatterns = [
    path('speech_recognition/',speech_recognition, name='speech_recognition')
]