from django.urls import path
from accounts import views

urlpatterns = [
    path('kakao/login/', views.kakao_login),
    path('kakao/callback/', views.kakao_callback),
    path('kakao/logout/', views.kakao_logout),
    path('userinfo/',views.user_info),
    path('userinfo/',views.check_jwt_user),
    path('tempuserinfo/',views.call_temp_user_info),
    path('tempuserlogin/',views.temp_user_login),
]