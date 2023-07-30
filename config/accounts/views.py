import requests
from django.shortcuts import redirect
from django.conf import settings
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
        username = profile_json["id"]
        nickname = profile_json['kakao_account']["profile"]["nickname"]
        email = profile_json["kakao_account"]["email"]
    else:
        raise ValueError(profile_request.status_code)
    """
    kakao_account에서 이메일 외에
    카카오톡 프로필 이미지, 배경 이미지 url 가져올 수 있음
    print(kakao_account) 참고
    """

    #username = payload_data.get('nickname')
    #email = payload_data.get('email')
    """
    Signup or Signin Request
    """
    try:
        user = User.objects.get(username=username)
        # 기존에 가입된 유저의 Provider가 kakao가 아니면 에러 발생, 맞으면 로그인
        # 다른 SNS로 가입된 유저
        social_user = SocialAccount.objects.get(user=user)
        if social_user is None:
            return JsonResponse({'err_msg': 'email exists but not social user'}, status=status.HTTP_400_BAD_REQUEST)
        # if social_user.provider != 'kakao':
        #     return JsonResponse({'err_msg': 'no matching social type'}, status=status.HTTP_400_BAD_REQUEST)
        # 기존에 Google로 가입된 유저
        data = {'access_token': access_token, 'code': code}
        accept = requests.post(
            f"{BASE_URL}accounts/kakao/login/finish/", data=data)
        accept_status = accept.status_code
        if accept_status != 200:
            return JsonResponse({'err_msg': 'failed to signin'}, status=accept_status)
        accept_json = accept.json()
        accept_json.pop('user', None)
        return JsonResponse(accept_json)
    except User.DoesNotExist:
        # 기존에 가입된 유저가 없으면 새로 가입
        data = {'access_token': access_token, 'code': code}
        accept = requests.post(
            #f"{BASE_URL}accounts/kakao/login/finish/", data=data)
            f"http://127.0.0.1:8000/accounts/kakao/login/finish/", data=data)
        accept_status = accept.status_code
        if accept_status != 200:
            #return JsonResponse({'err_msg': 'failed to signup'}, status=accept_status)
            raise Exception(accept.status_code)
        # user의 pk, email, first name, last name과 Access Token, Refresh token 가져옴
        accept_json = accept.json()
        accept_json.pop('user', None)
        return JsonResponse(accept_json)


class KakaoLogin(SocialLoginView):
    adapter_class = kakao_view.KakaoOAuth2Adapter
    client_class = OAuth2Client
    callback_url = KAKAO_CALLBACK_URI
