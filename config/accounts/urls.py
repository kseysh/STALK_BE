from django.urls import path
from accounts import views

urlpatterns = [
    path('kakao/signin/', views.kakao_login, name='kakao_login'),
    path('callback/', views.kakao_callback, name='kakao_callback'),
    path('kakao/login/finish/', views.KakaoLogin.as_view(),
         name='kakao_login_todjango'),

]