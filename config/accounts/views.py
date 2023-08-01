import requests
from django.shortcuts import redirect
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.kakao import views as kakao_view
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.models import SocialAccount
from .models import User

# if settings.DEBUG:
#     BASE_URL = 'http://localhost:8000/'
# else:
BASE_URL = 'https://stalksound.store/'

KAKAO_CALLBACK_URI = 'http://stalksound.store/accounts/callback'

def create_token(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def kakao_login(request):
    rest_api_key = settings.KAKAO_REST_API_KEY
    return redirect(
        f"https://kauth.kakao.com/oauth/authorize?client_id={rest_api_key}&redirect_uri={KAKAO_CALLBACK_URI}&response_type=code"
    )


def kakao_callback(request):
    rest_api_key = settings.KAKAO_REST_API_KEY
    client_secret_key = settings.KAKAO_CLIENT_SECRET_KEY
    code = request.GET.get("code")


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
    # return JsonResponse({
    #     "token":token_req_json
    # })

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
        nickname = profile_json['kakao_account']["profile"]["nickname"]
        email = profile_json["kakao_account"].get("email")
    else:
        raise ValueError(profile_request.status_code)
    try:
        user = User.objects.get(username=username)
        token = create_token(user=user)
        data = {'access_token': access_token, 'code': code}
        accept = requests.post(
            f"{BASE_URL}accounts/kakao/finish/", data=data)
        accept_json = accept.json()
        return JsonResponse(accept_json)
    except User.DoesNotExist:
        data = {'access_token': access_token, 'code': code}
        accept = requests.post(
            f"{BASE_URL}accounts/kakao/finish/", data=data)
        accept_json = accept.json()
        return JsonResponse(accept_json)


# class KakaoLogin(SocialLoginView):
#     adapter_class = kakao_view.KakaoOAuth2Adapter
#     client_class = OAuth2Client