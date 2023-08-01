from django.urls import path
from accounts import views

urlpatterns = [
    path('kakao/signin/', views.kakao_login),
    path('callback/', views.kakao_callback),
    path('kakao/finish/', views.KakaoLogin.as_view()),

]