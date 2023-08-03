from django.urls import path
from accounts import views

urlpatterns = [
    path('kakao/login/', views.kakao_login),
    path('callback/', views.kakao_callback),
    path('kakao/logout/', views.kakao_logout),

]