from django.contrib import admin
from django.urls import path, re_path
from django.urls import include
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('restauth/', include('dj_rest_auth.urls')),
    path('regauth/', include('dj_rest_auth.registration.urls')),
    path('allauth/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),

]# 로그아웃 시에는 /accounts/logout으로 요청한다.

if not settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)