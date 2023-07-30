import requests
from django.shortcuts import redirect
from django.conf import settings
from django.contrib import auth
from django.http import JsonResponse
from rest_framework import status
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.kakao import views as kakao_view
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.models import SocialAccount
from .models import User

if not settings.DEBUG:
    BASE_URL = 'http://localhost:8000/'
else:
    BASE_URL = 'https://stalksound.store/'

#KAKAO_CALLBACK_URI = 'http://localhost:8000/accounts/kakao/callback/'
KAKAO_CALLBACK_URI = 'http://127.0.0.1:8000/accounts/callback/'

def kakao_login(request):
    rest_api_key = settings.KAKAO_REST_API_KEY
    return redirect(
        f"https://kauth.kakao.com/oauth/authorize?client_id={rest_api_key}&redirect_uri={KAKAO_CALLBACK_URI}&response_type=code"
    )


def kakao_callback(request):
    rest_api_key = settings.KAKAO_REST_API_KEY
    client_secret_key = settings.KAKAO_CLIENT_SECRET_KEY
    code = request.GET.get("code")
    #code = request.GET["code"]
    kakao_token_uri = "https://kauth.kakao.com/oauth/token"
    """
    Access Token Request
    """
    request_data = {
            'grant_type': 'authorization_code',
            'client_id': rest_api_key,
            'redirect_uri': KAKAO_CALLBACK_URI,
            'client_secret': client_secret_key,
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
    #access_token = token_req_json.get("access_token")
    access_token = token_req_json["access_token"]

    """
    Email Request
    """
    profile_request = requests.get(
        "https://kapi.kakao.com/v2/user/me", 
        headers={"Authorization": f"Bearer ${access_token}",
                 "Content-type": "application/x-www-form-urlencoded;charset=utf-8"},
                 )
    if profile_request.status_code == 200:
        profile_json = profile_request.json()
        error = profile_json.get("error")
        if error is not None:
            raise ValueError(error)
        user_id = profile_json["id"]
        user_nickname = profile_json['kakao_account']["profile"]["nickname"]
        user_email = profile_json["kakao_account"].get("email")
    else:
        raise ValueError(profile_request.status_code)

    try: # 이미 회원가입이 된 유저를 로그인 처리
        user = User.objects.get(user_id=user_id) # 만약 username이 같은 유저가 없다면

        auth.login(user)

        user_data = {
            'user_id':user_id,
            'user_email':user_email,
            'user_nickname':user_nickname
        }
        
        return JsonResponse(user_data)
    except User.DoesNotExist:
        user = User.objects.create_user(
            user_id = user_id,
            user_email = user_email,
            user_nickname = user_nickname
        )

        auth.login(user)

        user_data = {
            'user_id':user_id,
            'user_email':user_email,
            'user_nickname':user_nickname
        }

        return JsonResponse(user_data)


class KakaoLogin(SocialLoginView):
    adapter_class = kakao_view.KakaoOAuth2Adapter
    client_class = OAuth2Client
    callback_url = KAKAO_CALLBACK_URI

