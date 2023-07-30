from rest_framework_simplejwt.views import TokenViewBase
from .serializers import CustomTokenRefreshSerializer


class CustomTokenRefreshView(TokenViewBase):

    serializer_class = CustomTokenRefreshSerializer