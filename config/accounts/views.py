import requests, jwt

from django.shortcuts import redirect
from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework import status,permissions 
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view,permission_classes,authentication_classes

from .models import User
from .serializers import UserSerializer


# BASE_URL = 'https://stalksound.store/'
# BASE_URL = 'http://127.0.0.1:8000/'
# KAKAO_CALLBACK_URI = 'https://stalksound.store/accounts/kakao/callback'
# KAKAO_CALLBACK_URI = 'http://127.0.0.1:8000/accounts/kakao/callback'
KAKAO_CALLBACK_URI = 'http://localhost:3000/kakao/callback'
# KAKAO_CALLBACK_URI = 'https://stalk-login-test.pages.dev/kakao/callback'

@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def kakao_login(request): # 백엔드 테스트용 login 코드 이 코드는 프론트에서 처리하도록 하기
    rest_api_key = settings.KAKAO_REST_API_KEY
    return redirect(
        f"https://kauth.kakao.com/oauth/authorize?client_id={rest_api_key}&redirect_uri={KAKAO_CALLBACK_URI}&response_type=code"
    )

@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def kakao_callback(request):
    rest_api_key = settings.KAKAO_REST_API_KEY
    code = request.GET.get("code")
    kakao_token_uri = "https://kauth.kakao.com/oauth/token"

    request_data = {
            'grant_type': 'authorization_code',
            'client_id': rest_api_key,
            'redirect_uri': KAKAO_CALLBACK_URI,
            'code': code,
        }
    token_headers = {
            'Content-type': 'application/x-www-form-urlencoded;charset=utf-8'
        }
    token_req = requests.post(kakao_token_uri, data=request_data, headers=token_headers)
    token_req_json = token_req.json()
    error = token_req_json.get("error")

    if error is not None:
        raise ValueError(error)
    access_token = token_req_json["access_token"]
    profile_request = requests.get(
        "https://kapi.kakao.com/v2/user/me", 
        headers={"Authorization": f"Bearer ${access_token}",})
    if profile_request.status_code == 200:
        profile_json = profile_request.json()
        error = profile_json.get("error")
        if error is not None:
            raise ValueError(error)
        username = profile_json["id"]
        user_nickname = profile_json['kakao_account']["profile"]["nickname"]
        user_email = profile_json["kakao_account"].get("email")
    else:
        raise ValueError(profile_request.status_code)
    try:
        user = User.objects.get(username=username)
        user_serializer = UserSerializer(user)
        token = TokenObtainPairSerializer.get_token(user)
        refresh_token = str(token)
        access_token = str(token.access_token)
        res = Response(
            {
                "user": user_serializer.data,
                "message": "login successs",
                "token": {
                    "access": access_token,
                    "refresh": refresh_token,
                },
            },
            status=status.HTTP_200_OK,
        )
        res.set_cookie("accessToken", value=access_token, max_age=None, expires=None, secure=True, samesite=None, httponly=True)
        res.set_cookie("refreshToken", value=refresh_token, max_age=None, expires=None, secure=True, samesite=None,httponly=True)
        return res
    except User.DoesNotExist:
        user = User.objects.create_user(username=username)
        user.username = username
        user.user_email = user_email
        user.user_nickname = user_nickname
        user.save()
        user_serializer = UserSerializer(user)
        token = TokenObtainPairSerializer.get_token(user)
        refresh_token = str(token)
        access_token = str(token.access_token)
        res = Response(
            {
                "user": user_serializer.data,
                "message": "register successs",
                "token": {
                    "access": access_token,
                    "refresh": refresh_token,
                },
            },
            status=status.HTTP_200_OK,
        )
        res.set_cookie("accessToken", access_token, httponly=True,secure=True,samesite=None)
        res.set_cookie("refreshToken", refresh_token, httponly=True,secure=True,samesite=None)

        return res
    
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
# @permission_classes([permissions.IsAuthenticated])
@permission_classes([permissions.AllowAny])
def kakao_logout(self):
    response = Response({
        "message": "Logout success"
        }, status=status.HTTP_202_ACCEPTED)
    response.delete_cookie("accessToken")
    response.delete_cookie("refreshToken")
    return response

@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
# @permission_classes([permissions.IsAuthenticated])
@permission_classes([permissions.AllowAny])
def check_jwt_user(request):
    # access = request.COOKIES['accessToken']
    # return 
    try:
        access = request.COOKIES['accessToken']
        payload = jwt.decode(access, settings.SECRET_KEY, algorithms=['HS256'])
        username = payload.get('username')
        user = get_object_or_404(User, username=username)
        serializer = UserSerializer(instance=user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except(jwt.exceptions.ExpiredSignatureError):
        data = {'refresh': request.COOKIES.get('refreshToken', None)}
        serializer = TokenRefreshSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            access = serializer.data.get('accessToken', None)
            refresh = serializer.data.get('refreshToken', None)
            payload = jwt.decode(access, settings.SECRET_KEY, algorithms=['HS256'])
            username = payload.get('username')
            user = get_object_or_404(User, username=username)
            serializer = UserSerializer(instance=user)
            res = Response(serializer.data, status=status.HTTP_200_OK)
            res.set_cookie("accessToken", value=access, max_age=None, expires=None, secure=True, samesite=None, httponly=True)
            res.set_cookie("refreshToken", value=refresh, max_age=None, expires=None, secure=True, samesite=None,httponly=True)

            return res
        raise jwt.exceptions.InvalidTokenError


def post(request):
    user = User.objects.get(id=1)
    print(user)
    s = UserSerializer(user)
    print(s.data)
    return Response(s.data,status=200)
