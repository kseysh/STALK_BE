from .views import *
from django.urls import path

urlpatterns = [
    path('transaction_rank/',transaction_rank, name='transaction_rank'),
    path('now_data/',now_data, name='now_data'),
    path('day_data/', day_data, name='day_data'),
    path('a_day_data/', a_day_data, name='a_day_data'),
    path('minute_data/', minute_data, name='minute_data'),
    path('hmm__minute_data/', hmm__minute_data, name='hmm__minute_data'),
    path('a_minute_data/', a_minute_data, name='a_minute_data'),
    path('week_data/', week_data, name='week_data'),
    path('a_week_data/', a_week_data, name='a_week_data')
]