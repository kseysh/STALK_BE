from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
import requests, mojito, os
import numpy as np
from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import permissions 
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.openapi import Schema, TYPE_ARRAY, TYPE_NUMBER

from io import BytesIO
from scipy.io import wavfile
from django.http import HttpResponse, JsonResponse

from accounts.views import check_jwt
from .serializers import StockSerializer, RecordSerializer, UserStockSerializer

from accounts.models import User
from .models import PurchaseHistory, Stock, Record, UserStock

f = open("./koreainvestment.key")
lines = f.readlines()
key = lines[0].strip()
secret = lines[1].strip()
acc_no = lines[2].strip()
sound_secret = lines[3].strip()
f.close()

broker = mojito.KoreaInvestment(
    api_key=key,
    api_secret=secret,
    acc_no=acc_no,
    mock=True
)

#사인파 만드는 함수
def generate_sine_wave(duration, frequency, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    data = 0.5 * np.sin(2 * np.pi * frequency * t)
    scaled_data = (data * 32767).astype(np.int16)
    return scaled_data

def get_exchange_rate(request):
    payload=""
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'HHDFS76200200',
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price-detail?AUTH=&EXCD=NAS&SYMB=AAPL"#AUTH는 아무 값도 안들어가는 것이 맞나요?
    response = requests.request("GET", url, headers=headers, data=payload)
    response_data = response.json() 
    exchange_rate = response_data['output']['t_rate']
    return exchange_rate


@swagger_auto_schema(
    method='get',
    operation_id='사용자의 정보 조회',
    operation_description='보유한 종목/기록 등',
    tags=['내정보'],
)
@api_view(['GET'])
def user_info(request):
    print("user_info start")
    try:
        user_id = check_jwt(request)
        print("user_id",user_id)
        if user_id==0:
            print("wrong_info",user_id)
            return Response({"detail":"잘못된 로그인 정보입니다."},status=401)
        user = User.objects.get(id=user_id)
        print("user ok", user)
        user_liked_stocks = Stock.objects.filter(liked_user=user)
        liked_stock_data=[]
        for stock in user_liked_stocks:
            image_path = os.path.join(settings.MEDIA_ROOT, f'{stock.symbol}.jpg')
            if os.path.isfile(image_path):
                image_url = f'https://stalksound.store/image/{stock.symbol}.jpg'
            else:
                image_url = 'https://stalksound.store/image/default.jpg'
            data =  {'prdt_name': stock.name, 'code': stock.symbol, 'is_domestic_stock': stock.is_domestic_stock ,'stock_image':image_url, }
            liked_stock_data.append(data)
    
        try:
            user_stocks = UserStock.objects.filter(user=user)
            user_stock_data = []
            
            exchange_rate = get_exchange_rate(request)
            for user_stock in user_stocks:
                if user_stock.stock.symbol.isdigit():
                    broker = mojito.KoreaInvestment(
                    api_key=key,
                    api_secret=secret,
                    acc_no=acc_no,
                    exchange="서울",
                    mock=True
                    )
                    resp = broker.fetch_price(user_stock.stock.symbol)
                    if user_stocks is not None:
                        if user_stock.having_quantity >= 1:
                            now_stock_price=int(resp['output']['stck_prpr']) * user_stock.having_quantity
                            user_stock.profit_loss = user_stock.price - now_stock_price
                            user_stock.now_price = now_stock_price
                            user_stock.rate_profit_loss=(now_stock_price-user_stock.price)/user_stock.price*100
                            print(user_stock.stock.name)
                            user_stock.save()
                    else:
                        pass
                else:
                    broker = mojito.KoreaInvestment(
                    api_key=key,
                    api_secret=secret,
                    acc_no=acc_no,
                    exchange="나스닥",
                    mock=True
                    )
                    resp = broker.fetch_oversea_price(user_stock.stock.symbol)
                    if user_stocks is not None:
                        if user_stock.having_quantity >= 1:
                            now_stock_price=int(float(resp['output']['last'])*float(exchange_rate)) * user_stock.having_quantity
                            user_stock.profit_loss = user_stock.price - now_stock_price
                            user_stock.now_price = now_stock_price
                            user_stock.rate_profit_loss=((now_stock_price-user_stock.price)/user_stock.price)*100
                            print(user_stock.stock.name)
                            user_stock.save()
                    else:
                        pass
            for user_stock in user_stocks:
                image_path = os.path.join(settings.MEDIA_ROOT, f'{user_stock.stock.symbol}.jpg')
                if os.path.isfile(image_path):
                    image_url = f'https://stalksound.store/image/{user_stock.stock.symbol}.jpg'
                else:
                    image_url = 'https://stalksound.store/image/default.jpg'
                user_stock_data.append({
                    'stock':user_stock.stock.name,
                    'stock_code':user_stock.stock.symbol,
                    'is_domestic_stock':user_stock.stock.is_domestic_stock,
                    'user':user_stock.user.user_nickname,
                    'stock_image':image_url,
                    'having_quantity': user_stock.having_quantity,
                    'price' : user_stock.price,
                    'now_price' : user_stock.now_price,
                    'profit_loss' : user_stock.profit_loss,
                    'rate_profit_loss' : user_stock.rate_profit_loss
                })
        except UserStock.DoesNotExist:
            user_stock_data = None
        
        try:
            record = Record.objects.filter(user=user)
            record_data = RecordSerializer(record, many=True).data
        except Record.DoesNotExist:
            record_data = None
        

        total_now_price = UserStock.objects.filter(user=user).aggregate(total_now_price=Sum('now_price'))['total_now_price'] or 0.0

        user_data = {
            'username': user.username,
            'user_nickname': user.user_nickname,
            'user_property': user.user_property,
            '총자산' : total_now_price
        }
        
        return Response({'유저정보': user_data,'찜한목록': liked_stock_data,'모의투자한 종목' : user_stock_data , '거래 기록' : record_data})
    
    except User.DoesNotExist:
        return Response({'error': '로그인 하세요.'}, status=403)


####매도####
@swagger_auto_schema(
    method='post',
    operation_id='매도',
    operation_description='매도하기',
    tags=['매수/매도/좋아요'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'stock_symbol': openapi.Schema(type=openapi.TYPE_STRING),
            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
        },
        required=['stock_symbol', 'quantity']
    )
)
@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])
def sell(request):
    stock_symbol = request.data.get('stock_symbol')
    quantity = request.data.get('quantity')
    user_id = check_jwt(request)
    if user_id==0:
        return Response({"detail":"잘못된 로그인 정보입니다."},status=401)
    user = User.objects.get(id=user_id)
    exchange_rate = get_exchange_rate(request)
    if stock_symbol.isdigit(): #숫자일때, 국내
        broker = mojito.KoreaInvestment(
            api_key=key,
            api_secret=secret,
            acc_no=acc_no,
            exchange="서울",
            mock=True
        )
        resp = broker.fetch_price(stock_symbol)
        to_price = int(resp['output']['stck_prpr'])*quantity
    else: #문자일때, 해외
        broker = mojito.KoreaInvestment(
            api_key=key,
            api_secret=secret,
            acc_no=acc_no,
            exchange="나스닥",
            mock=True
        )
        resp = broker.fetch_oversea_price(stock_symbol)
        to_price = int(float((resp['output']['last']))*float(exchange_rate))*quantity
    per_one_price = to_price/quantity
    user_id = check_jwt(request)
    if user_id==0:
        return Response({"detail":"잘못된 로그인 정보입니다."},status=401)
    user = User.objects.get(id=user_id)
    # user = User.objects.get(id=2)
    if(quantity<=0):
        return Response({"error": "양수값을 넣어라"})
    try:
        stock = Stock.objects.get(symbol=stock_symbol)
    except Stock.DoesNotExist:
        return Response({"error": "없는 종목입니다"}, status=400)
    try:
        user_stock = UserStock.objects.get(user=user, stock=stock)
    except UserStock.DoesNotExist:
        return Response({"error": "해당 종목을 보유하고 있지 않습니다"}, status=400)
    purchase_history = PurchaseHistory.objects.create(
        user=user,
        stock=stock,
        quantity=quantity,
        per_one_price=per_one_price
    )
    purchase_histories = PurchaseHistory.objects.filter(user=user, stock=stock)

    total_price = 0
    total_quantity = 0
    for history in purchase_histories:
        total_price += history.per_one_price * history.quantity
        total_quantity += history.quantity
    if total_quantity > 0:
        avg_price = total_price / total_quantity

    if  user_stock.having_quantity>= quantity:
        user_stock.having_quantity -= quantity
        user.user_property += user_stock.now_price
        user_stock.price = user_stock.having_quantity*avg_price
        user_stock.now_price = user_stock.having_quantity*per_one_price
        user.save()
        user_stock.save()
        if user_stock.having_quantity <=0:
            user_stock.delete()
            purchase_histories.delete()
    else:
        return Response({"error": "종목 보유량보다 큰 값을 입력 받았습니다"}, status=400)

    record = Record.objects.create(
        user = user,
        stock = stock,
        transaction_type = '판매',
        quantity = quantity,
        price = to_price,
        left_money = user.user_property
    )
    stock_data = StockSerializer(stock).data
    user_stock_data = UserStockSerializer(user_stock).data
    record_data = RecordSerializer(record).data
    return Response({"message": "판매완료","stock": stock_data,"user_stock": user_stock_data, "record": record_data}, status=200)

####매수####
@swagger_auto_schema(
    method='post',
    operation_id='매수',
    operation_description='매수하기',
    tags=['매수/매도/좋아요'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'stock_symbol': openapi.Schema(type=openapi.TYPE_STRING),
            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
        },
        required=['stock_symbol', 'quantity']
    )
)
@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])
def buy(request):
    stock_symbol = request.data.get('stock_symbol')
    quantity = request.data.get('quantity')
    user_id = check_jwt(request)
    if user_id==0:
        return Response({"detail":"잘못된 로그인 정보입니다."},status=401)
    user = User.objects.get(id=user_id)
    exchange_rate = get_exchange_rate(request)
    if stock_symbol.isdigit():#숫자일때, 국내
        broker = mojito.KoreaInvestment(
            api_key=key,
            api_secret=secret,
            acc_no=acc_no,
            exchange="서울",
            mock=True
        )
        resp = broker.fetch_price(stock_symbol)
        to_price = int(float(resp['output']['stck_prpr']))*quantity
    else: #문자일때, 해외
        broker = mojito.KoreaInvestment(
            api_key=key,
            api_secret=secret,
            acc_no=acc_no,
            exchange="나스닥",
            mock=True
        )
        resp = broker.fetch_oversea_price(stock_symbol)
        to_price = int(float(resp['output']['last'])*float(exchange_rate))*quantity
    per_one_price = to_price/quantity
    user_id = check_jwt(request)
    if user_id==0:
        return Response({"detail":"잘못된 로그인 정보입니다."},status=401)
    user = User.objects.get(id=user_id)
    # user = User.objects.get(id=1)
    if(quantity<=0):
        return Response({"error": "양수값을 넣어라"})
    try:
        stock = Stock.objects.get(symbol=stock_symbol)
    except Stock.DoesNotExist:
        return Response({"error": "없는 종목입니다"}, status=400)

    if user.user_property >= to_price:
        user.user_property -= to_price
        user.save()
    else:
        return Response({"error":"잔액부족"}, status=400)
    
    purchase_history = PurchaseHistory.objects.create(
        user=user,
        stock=stock,
        quantity=quantity,
        per_one_price=per_one_price
    )
    purchase_histories = PurchaseHistory.objects.filter(user=user, stock=stock)

    total_price = 0
    total_quantity = 0
    for history in purchase_histories:
        total_price += history.per_one_price * history.quantity
        total_quantity += history.quantity
    if total_quantity > 0:
        avg_price = total_price / total_quantity
    
    try:
        user_stock = UserStock.objects.get(user=user, stock=stock)
        user_stock.having_quantity += quantity
        user_stock.save()
        user_stock.price = avg_price * user_stock.having_quantity
        user_stock.now_price = user_stock.having_quantity*per_one_price
        user_stock.save()
    except UserStock.DoesNotExist:
        user_stock = UserStock.objects.create(
        user=user,
        price = to_price,
        stock=stock,
        having_quantity=quantity,
        profit_loss=0,
        now_price = to_price,
        rate_profit_loss = 0
        )

    record = Record.objects.create(
        user = user,
        stock = stock,
        transaction_type = '구매',
        quantity = quantity,
        price = to_price,
        left_money = user.user_property
    )

    
    stock_data = StockSerializer(stock).data
    user_stock_data = UserStockSerializer(user_stock).data
    record_data = RecordSerializer(record).data
    return Response({"message": "구매완료","stock": stock_data,"user_stock": user_stock_data, "record": record_data}, status=200)

####좋아요####
@swagger_auto_schema(
    method='post',
    operation_id='찜(좋아요) 기능',
    operation_description='종목 이름을 넣으세요',
    tags=['매수/매도/좋아요'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'symbol': openapi.Schema(type=openapi.TYPE_STRING),
        },
        required=['symbol']
    )
)
@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])
def like_stock(request):
    stock_symbol = request.data.get('symbol')
    try:
        stock = Stock.objects.get(symbol=stock_symbol)
    except Stock.DoesNotExist:
        return Response(status=404)
    user_id = check_jwt(request)
    if user_id==0:
        return Response({"detail":"잘못된 로그인 정보입니다."},status=401)
    user = User.objects.get(id=user_id)
    # user = User.objects.get(id=2)
    if user in stock.liked_user.all():
        stock.liked_user.remove(user)
        return Response({'message': '찜 취소 완료'})
    else:
        stock.liked_user.add(user)  
        stock.likes += 1
    stock.save()
    return Response({'message': '찜 완료'})

###############################SONIFICATION################################

####차트 음향화####
@swagger_auto_schema(
    method='post',
    operation_id='현재가 데이터 음향화',
    operation_description='데이터를 소리로 변환',
    tags=['음성'],
    request_body=Schema(
        type='object', 
        properties={
            'lista': Schema(
                type=TYPE_ARRAY,
                items=Schema(
                    type=TYPE_NUMBER,
                ),
            ),
        },
        required=['lista'],
    ),
)
@api_view(['POST'])
def data_to_sound(request):
    data = request.data.get('lista')
    duration = 0.4
    result = generate_sine_wave(0.1, 0)  # 사인파들을 numpy.ndarray 형태로 받아올 빈 numpy.ndarray
    min_value = min(data)
    max_value = max(data)
    adjusted_data = [(value - min_value-70) / (max_value - min_value) * 2000 for value in data]
    
    for i in adjusted_data:
        # 스케일을 조정하여 큰 값으로 변환
        sine = generate_sine_wave(duration, i)
        result = np.concatenate((result, sine))
    
    wav_stream = BytesIO()
    wavfile.write(wav_stream, 44100, result)
    wav_bytes = wav_stream.getvalue()

    response = HttpResponse(content_type='audio/wav') ##audio 타입 설정
    response['Content-Disposition'] = 'attachment; filename="output.wav"'
    response.write(wav_bytes)
    return response

class CheckIsLike(APIView): 
    stock_name= openapi.Parameter('stock_name', openapi.IN_QUERY, description='종목 이름', required=True, type=openapi.TYPE_STRING)
    @swagger_auto_schema(tags=['좋아요가 눌려져 있는 주식인지 확인하는 기능'],manual_parameters=[stock_name], responses={200: 'Success'})
    def get(self, request):
        user_id = check_jwt(request)
        if user_id==0:
            return Response({"detail":"잘못된 로그인 정보입니다."},status=401)
        user = User.objects.get(id=user_id)
        # user = User.objects.get(id=2)
        stock_name = request.GET.get("stock_name")
        stock = Stock.objects.get(symbol=stock_name)
        if user in stock.liked_user.all():
            return Response({'message': True}, status=200)
        else:
            return Response({'message': False}, status=200)

@swagger_auto_schema(
    method='post',
    operation_id='음성을 텍스트로 변환',
    operation_description='사용자의 음성을 텍스트로 변환',
    tags=['음성'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT, 
        properties={
            'audio': openapi.Schema(
                type=openapi.TYPE_FILE,
            ),
        },
        required=['audio'],
    ),
)
@api_view(['POST'])
def speech_to_text(request):
    # data = open("your/path/to/voice.mp3", "rb") # STT를 진행하고자 하는 음성 파일


    Lang = "Kor" # Kor / Jpn / Chn / Eng
    URL = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=" + Lang
        
    ID = "qcxc89t0bs" # 인증 정보의 Client ID
    Secret = "vgU8vBup9zR8gFURTxisFeOHDhgfKNuxe2V8GraT" # 인증 정보의 Client Secret
        
    headers = {
        "Content-Type": "application/octet-stream", # Fix
        "X-NCP-APIGW-API-KEY-ID": ID,
        "X-NCP-APIGW-API-KEY": Secret,
    }
    audio_file = request.FILES.get('audio')

    response = requests.post(URL, data=audio_file.read(), headers=headers)
    rescode = response.status_code
    if rescode == 200:
        return Response(response.text)

@swagger_auto_schema(
    method='get',
    operation_id='초기 데이터베이스 설정',
    operation_description='국내/해외 시총 100개씩 데이터베이스에 생성',
    tags=['데이터베이스 설정']
)
@api_view(['GET'])
def create_stock_database(request):
    ## 국내 주식 시총기준 100위 데이터베이스 생성 ##
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'HHKST03900400'
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/psearch-result?user_id=@2108665&seq=0"
    response = requests.get(url, headers=headers)
    response_data = response.json() 
    transaction_data_list = []
    for item in response_data['output2']:
        data = {
            '종목명': item['name'],
            '종목코드': item['code'],
            '시가총액' : float(item['stotprice']),
            '현재가':float(item['price']),
            '전일 대비율': float(item['chgrate']),
            '대비': float(item['change']),
        }
        stock= Stock.objects.create(
            symbol=item['code'],
            name=item['name'],
            is_domestic_stock = True,
            stock_image=f'{item["code"]}.jpg'
            )
        try:
            like=stock.likes
            data['좋아요 개수'] = like
            transaction_data_list.append(data)
        except IntegrityError:
            data['좋아요 개수'] = 0
            pass

    ## 해외 주식 시총기준 100위 데이터베이스 생성 ##
    headers = {
        'content-type': 'application/json',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'HHDFS76410000',
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-search?AUTH=&EXCD=NAS&CO_YN_PRICECUR=&CO_ST_PRICECUR=&CO_EN_PRICECUR=&CO_YN_RATE=&CO_ST_RATE=&CO_EN_RATE=&CO_YN_VALX=1&CO_ST_VALX=0&CO_EN_VALX=100000000000000&CO_YN_SHAR=&CO_ST_SHAR=&CO_EN_SHAR=&CO_YN_VOLUME=&CO_ST_VOLUME=&CO_YN_AMT=&CO_EN_VOLUME=&CO_ST_AMT=&CO_EN_AMT=&CO_YN_EPS=&CO_ST_EPS=&CO_EN_EPS=&CO_YN_PER=&CO_ST_PER=&CO_EN_PER="
    response = requests.get(url, headers=headers)
    response_data = response.json() 
    f_transaction_data_list = []
    exchange_rate = get_exchange_rate(request)
    for item in response_data['output2']:
        data = {
            '종목명': item['name'],
            '종목코드': item['symb'],
            '시가총액 순위': item['rank'],
            '시가총액' : float(item['valx']),
            '현재가': float(item['last']),
            '전일 대비율': float(item['rate']),
            '대비': float(item['diff']),
            '환율':exchange_rate,
        }
        try:
            stock = Stock.objects.create(
            symbol=item['symb'],
            name=item['name'],
            is_domestic_stock = False,
            stock_image=f'{item["symb"]}.jpg'
            )
            data['좋아요 개수'] = 0
            f_transaction_data_list.append(data)
        except IntegrityError:
            pass

    return Response({'국내 시가총액 순위': transaction_data_list,
                    '해외 시가총액 순위': f_transaction_data_list,})


class StockAPIView(APIView):
    is_domestic_stock = openapi.Parameter('is_domestic_stock', openapi.IN_QUERY, description='is_domestic_stock True/False면 국내/해외 주식 리스트', required=True, type=openapi.TYPE_STRING)
    @swagger_auto_schema(tags=['Stock의 전체 리스트를 불러오는 기능'],manual_parameters=[is_domestic_stock], responses={200: 'Success'})
    def get(self, request):
        req = request.GET.get('is_domestic_stock')
        result = []
        stocks = Stock.objects.filter(is_domestic_stock=req)
        for item in stocks:
            data = {
                'prdt_name':item.name,
                'code':item.symbol,
            }
            result.append(data)
        return Response(result)