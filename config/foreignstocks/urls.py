from .views import *
from django.urls import path

urlpatterns = [
    path('f_transaction_rank/',f_transaction_rank, name='f_transaction_rank'),
    path('f_now_data/',f_now_data, name='f_now_data'),
    path('f_day_data/', f_day_data, name='f_day_data'),
    path('f_a_day_data/', f_a_day_data, name='f_a_day_data'),
    path('f_a_minute_data/', f_a_minute_data, name='f_a_minute_data'),
    path('f_minute_data/', f_minute_data, name='f_minute_data'),
    path('f_a_week_data/', f_a_week_data, name='f_a_week_data'),
    path('f_week_data/', f_week_data, name='f_week_data'),
]