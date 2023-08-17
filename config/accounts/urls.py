from django.urls import path
from accounts import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    path('kakao/login/', views.kakao_login),
    path('kakao/callback/', views.kakao_callback),
    path('kakao/logout/', views.kakao_logout),
    path('userinfo/',views.user_info),
    path('tempuserlogin/',views.temp_user_login),
    path('test403/',views.test403),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]