from django.urls import path
from accounts import views

urlpatterns = [
    path('kakao/login/', views.kakao_login),
    path('kakao/callback/', views.kakao_callback),
    path('kakao/logout/', views.kakao_logout),
    path('userinfo/',views.check_jwt_user),

]