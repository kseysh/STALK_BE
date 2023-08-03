from django.contrib import admin
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path,include,re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

schema_view = get_schema_view(
    openapi.Info(
        title="STALK API 명세서",
        default_version='v1',
        description="유선마우스 화이팅!",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    path('restauth/', include('dj_rest_auth.urls')),
    path('regauth/', include('dj_rest_auth.registration.urls')),
    path('allauth/', include('allauth.urls')),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), 
    #access token과 refresh token을 받을 수 있도록 함
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    #access token을 이용하여 두 토큰을 재발급
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    #클라이언트가 서버 쪽 signing key가 없이 토큰을 검증할 수 있도록 함
    path('dj_rest-auth',include('dj_rest_auth.urls')),
    path('dj_rest-auth/registration/',include('dj_rest_auth.registration.urls')),


    #path('conversion/', include('conversion.urls')),
    path('accounts/', include('accounts.urls')),
    #path('sonification/', include("sonification.urls")),

    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]# 로그아웃 시에는 /accounts/logout으로 요청한다.

if not settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
