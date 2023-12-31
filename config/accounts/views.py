import requests, jwt

from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.http import JsonResponse

from rest_framework import status,permissions 
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from .models import User
from transaction.models import Stock, Record, UserStock
from .serializers import UserSerializer
from transaction.serializers import RecordSerializer, UserStockSerializer


# BASE_URL = 'https://stalksound.store/'
# BASE_URL = 'http://127.0.0.1:8000/'
# KAKAO_CALLBACK_URI = 'https://stalksound.store/accounts/kakao/callback'
# KAKAO_CALLBACK_URI = 'http://127.0.0.1:8000/accounts/kakao/callback'
# KAKAO_CALLBACK_URI = 'http://localhost:3000/kakao/callback'
# KAKAO_CALLBACK_URI = 'https://stalk-login-test.pages.dev/kakao/callback'
KAKAO_CALLBACK_URI = 'https://inhastalk.pages.dev/kakao/callback'

@api_view(['GET'])
def kakao_login(request): # 백엔드 테스트용 login 코드 이 코드는 프론트에서 처리하도록 하기
    rest_api_key = settings.KAKAO_REST_API_KEY
    return redirect(
        f"https://kauth.kakao.com/oauth/authorize?client_id={rest_api_key}&redirect_uri={KAKAO_CALLBACK_URI}&response_type=code"
    )

@api_view(['GET'])
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
        headers={"Authorization": f'Bearer {access_token}',
                 'Content-type': 'application/x-www-form-urlencoded;charset=utf-8'
                 })
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
        access_token = access_token

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
        res.set_cookie("accessToken", value=access_token, max_age=None, expires=None, secure=True, samesite="None", httponly=True)
        res.set_cookie("refreshToken", value=refresh_token, max_age=None, expires=None, secure=True, samesite="None",httponly=True)
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
        res.set_cookie("accessToken", value=access_token, max_age=None, expires=None, secure=True, samesite="None", httponly=True)
        res.set_cookie("refreshToken", value=refresh_token, max_age=None, expires=None, secure=True, samesite="None",httponly=True)

        return res
    
@api_view(['GET'])
def kakao_logout(self):
    response = Response({
        "message": "Logout success"
        }, status=status.HTTP_202_ACCEPTED)
    response.delete_cookie("accessToken")
    response.delete_cookie("refreshToken")

    return response

def check_jwt(request):
    try:
        print("check access")
        access = request.COOKIES['accessToken']
        print("check_jwt : access",access)
        payload = jwt.decode(access, settings.SECRET_KEY, algorithms=['HS256'])
        username = payload.get('username')
        user = get_object_or_404(User, username=username)
        user_id = user.id
        return user_id

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
            res = Response(serializer.data)
            res.set_cookie("accessToken", value=access, max_age=None, expires=None, secure=True, samesite="None", httponly=True)
            res.set_cookie("refreshToken", value=refresh, max_age=None, expires=None, secure=True, samesite="None",httponly=True)
            return user.id
        else:
            print("wrong jwt")
            return 0

@api_view(['GET'])
def temp_user_login(request):
    user = User.objects.get(id = 2)
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
    res.set_cookie("accessToken", value=access_token, max_age=None, expires=None, secure=True, samesite="None", httponly=True)
    res.set_cookie("refreshToken", value=refresh_token, max_age=None, expires=None, secure=True, samesite="None",httponly=True)
    return res

@api_view(['GET'])
def winner_winner_chicken_dinner(request):
    users = User.objects.order_by('user_property')
    serializer = UserSerializer(users,many=True)
    return Response(serializer.data, status=200)


@api_view(['GET'])
def user_info(request):
    try:
        user_id = check_jwt(request)
        if user_id==0:
            return Response({"detail":"잘못된 로그인 정보입니다."},status=401)
        user = User.objects.get(id=user_id)

        user_liked_stocks = Stock.objects.filter(liked_user=user)
        liked_stock_data = [{'prdt_name': stock.name, 'code': stock.symbol, 'is_domestic_stock': stock.is_domestic_stock} for stock in user_liked_stocks]
        try:
            user_stocks = UserStock.objects.filter(user=user)
            user_stock_data = UserStockSerializer(user_stocks, many=True).data
        except UserStock.DoesNotExist:
            user_stock_data = None
        try:
            record = Record.objects.filter(user=user)
            record_data = RecordSerializer(record, many=True).data
        except Record.DoesNotExist:
            record_data = None

        user_data = {
            'username': user.username,
            'user_nickname': user.user_nickname,
            'user_property': user.user_property,
        }
        
        return Response({'유저정보': user_data,'찜한목록': liked_stock_data,'모의투자한 종목' : user_stock_data , '거래 기록' : record_data})
    
    except User.DoesNotExist:
        return Response({'error': '로그인 하세요.'}, status=403)