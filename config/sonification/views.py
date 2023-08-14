import base64
import requests
import json
from io import BytesIO
import os
from django.conf import settings
import numpy as np
from scipy.io import wavfile
import mojito
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from .models import Stock, Record, UserStock
from accounts.models import User
from rest_framework.response import Response
from .serializers import StockSerializer, RecordSerializer, UserStockSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import permissions 
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.openapi import Schema, TYPE_ARRAY, TYPE_NUMBER
from rest_framework.parsers import MultiPartParser

f = open("./koreainvestment.key")
lines = f.readlines()
key = lines[0].strip()
secret = lines[1].strip()
acc_no = lines[2].strip()
f.close()

broker = mojito.KoreaInvestment(
    api_key=key,
    api_secret=secret,
    acc_no=acc_no,
    mock=True
)

#값의 변화량을 주파수로 치환하는 함수
def substitution(mx,mn,chart):
    lista = []
    for i in chart:        
        percentage = ((i - mn)/((mx-mn))) *200
        lista.append(percentage*10+100)
    return lista

#사인파 만드는 함수
def generate_sine_wave(duration, frequency, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    data = 0.5 * np.sin(2 * np.pi * frequency * t)
    scaled_data = (data * 32767).astype(np.int16)
    return scaled_data

##############################################################################################################

####거래량 순위####
url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/volume-rank?FID_COND_MRKT_DIV_CODE=J&FID_COND_SCR_DIV_CODE=20171&FID_INPUT_ISCD=0002&FID_DIV_CLS_CODE=0&FID_BLNG_CLS_CODE=0&FID_TRGT_CLS_CODE=111111111&FID_TRGT_EXLS_CLS_CODE=000000&FID_INPUT_PRICE_1=0&FID_INPUT_PRICE_2=0&FID_VOL_CNT=0&FID_INPUT_DATE_1=0"

f_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice?AUTH=&EXCD=NAS&SYMB={symbol}&NMIN=5&PINC=1&NEXT=&NREC=120&FILL=&KEYB="

payload = {}

f_payload = ""

headers = {
  'content-type': 'application/json',
  'authorization' : broker.access_token,
#   'authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ0b2tlbiIsImF1ZCI6IjQ2M2I2MjQyLTYzNzItNGZjNS04M2I2LWZhNjExNTQwOTFmOCIsImlzcyI6InVub2d3IiwiZXhwIjoxNjkxNzkxMTM5LCJpYXQiOjE2OTE3MDQ3MzksImp0aSI6IlBTd0dhNndIZERlTnRidk4ycUpFMWczMHg0OThtbkhoMUE2ViJ9.ZWTFzj2V-HbhyTMwUZohbFMxpd2Xr3CTAOdNTYlJGPDKAiQfKT5XaZp90noi1OZ0IIMTRHIxnpGsbWJxf7xPsg',
  'appkey': key,
  'appsecret': secret,
  'tr_id': 'FHPST01710000',
  'custtype': 'P'
}
@swagger_auto_schema(
    method='get',
    operation_id='거래량 순위(50개)',
    operation_description='거래량 순위(50개)',
    tags=['주식 데이터']
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def transaction_rank(request):
    response = requests.get(url, headers=headers)  # Use GET request
    response_data = response.json()  # Parse JSON response

    transaction_data_list = []

    for item in response_data['output']:
        data = {
            '종목명': item['hts_kor_isnm'],
            '거래량 순위': item['data_rank'],
            '현재가': item['stck_prpr'],
            '전일 대비율': item['prdy_ctrt'],
            '누적 거래량': item['acml_vol'],
        }
        transaction_data_list.append(data)

    
    return Response({'거래량 순위': transaction_data_list})

#그냥 현재가
@swagger_auto_schema(
    method='get',
    operation_id='현재 주가 확인 및 사용자 투자종목 업데이트',
    operation_description='api호출한 순간의 해당종목 데이터',
    tags=['주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
    ],
)

@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def now_data(request):
    symbol = request.GET.get('symbol')
    if not symbol:
        return JsonResponse({'error': 'Symbol not provided'}, status=400)
    resp = broker.fetch_price(symbol)
    chart_data = { 
        '전일대비부호': resp['output']['prdy_vrss_sign'],
        '전일 대비율': resp['output']['prdy_ctrt'],
        '시가': resp['output']['stck_oprc'],
        '현재가': resp['output']['stck_prpr'],
        '고가': resp['output']['stck_hgpr'],
        '저가': resp['output']['stck_lwpr']
    }
    stock = Stock.objects.get(symbol=symbol)
    user_stock = UserStock.objects.filter(stock=stock)

    if user_stock is not None:
        for user_stock in user_stock:
            if user_stock.having_quantity >= 1:
                now_stock_price=int(resp['output']['stck_prpr']) * user_stock.having_quantity
                user_stock.profit_loss = user_stock.price - now_stock_price
                user_stock.now_price = now_stock_price
                user_stock.rate_profit_loss=(now_stock_price-user_stock.price)/user_stock.price*100

                user_stock.save()
    else:
        pass
    return JsonResponse({'chart_data': chart_data}, safe=True)

##해외 현재상태 ##
@swagger_auto_schema(
    method='get',
    operation_id='(해외)현재 주가 확인 및 사용자 투자종목 업데이트',
    operation_description='api호출한 순간의 해당종목 데이터',
    tags=['(해외)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def f_now_data(request):
    symbol = request.GET.get('symbol')
    broker = mojito.KoreaInvestment(
    api_key=key,
    api_secret=secret,
    acc_no=acc_no,
    exchange="나스닥",
    mock=True
    )
    resp = broker.fetch_oversea_price(symbol)
    chart_data = { 
        '거래량': resp['output']['tvol'],
        '현재가': resp['output']['last'],
        '대비': resp['output']['diff'],
        '등락율': resp['output']['rate']
    }
    stock = Stock.objects.get(symbol=symbol)
    user_stock = UserStock.objects.filter(stock=stock)

    if user_stock is not None:
        for user_stock in user_stock:
            if user_stock.having_quantity >= 1:
                now_stock_price=float(resp['output']['last']) * user_stock.having_quantity
                user_stock.profit_loss = user_stock.price - now_stock_price
                user_stock.now_price = now_stock_price
                user_stock.rate_profit_loss=(now_stock_price-user_stock.price)/user_stock.price*100

                user_stock.save()
    else:
        return JsonResponse({'chart_data': chart_data}, safe=True)
    return JsonResponse({'chart_data': chart_data}, safe=True)

####일봉####
@swagger_auto_schema(
    method='get',
    operation_id='날짜 별 데이터 조회',
    operation_description='최대 100일 조회가능/ 시작일~종료일',
    tags=['주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
        openapi.Parameter('begin', in_=openapi.IN_QUERY, description='시작일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def day_data(request):
    symbol = request.GET.get('symbol')
    begin = request.GET.get('begin') 
    end = request.GET.get('end') 
    print(symbol)
    resp = broker.fetch_ohlcv(
        start_day=begin, #YYYYMMDD 형식 지킬 것
        end_day=end,
        symbol=symbol, #종목
        timeframe='D',  
        adj_price=True
    )
    daily_price = resp['output2']
    jm = resp['output1']['hts_kor_isnm']
    print(jm)
    chart= []
    data=[]
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            "종목": jm,
            '날짜': dp['stck_bsop_date'],
            '현재가': dp['stck_clpr'],
        }
        chart.append(int(dp['stck_clpr']))
        data.append(chart_data)
        mx = max(mx,int(dp['stck_hgpr']))
        mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

####해외 일별 ####

@swagger_auto_schema(
    method='get',
    operation_id='(해외)날짜 별 데이터 조회',
    operation_description='최대 100일 조회가능/ 시작일~종료일',
    tags=['(해외)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def f_day_data(request):
    symbol = request.GET.get('symbol')
    end = request.GET.get('end') 
    broker = mojito.KoreaInvestment(
    api_key=key,
    api_secret=secret,
    acc_no=acc_no,
    exchange="나스닥",
    mock=True
    )
    resp = broker.fetch_ohlcv_overesea(
        end_day=end,
        symbol=symbol, #종목
        timeframe='D',  
        adj_price=True
    )
    daily_price = resp['output2']
    chart= []
    data=[]
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            '날짜': dp['xymd'],
            '종가': dp['clos'],
        }
        chart.append(float(dp['clos']))
        data.append(chart_data)
        mx = max(mx,float(dp['high']))
        mn = min(mn,float(dp['low']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

####주봉####

@swagger_auto_schema(
    method='get',
    operation_id='주 별 데이터 조회',
    operation_description='일 별 데이터와 동일하게 최대 100개의 데이터 조회 가능',
    tags=['주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
        openapi.Parameter('begin', in_=openapi.IN_QUERY, description='시작일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def week_data(request):
    symbol = request.GET.get('symbol')
    begin = request.GET.get('begin') 
    end = request.GET.get('end') 
    print(symbol)
    resp = broker.fetch_ohlcv(
        start_day=begin, #YYYYMMDD 형식 지킬 것
        end_day=end,
        symbol=symbol, #종목
        timeframe='W',  
        adj_price=True
    )
    print(resp)
    daily_price = resp['output2']
    print(daily_price)
    jm = resp['output1']['hts_kor_isnm'] #종목 ㅋㅋ
    print(jm)
    chart= []
    data=[]
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            "종목": jm,
            '날짜': dp['stck_bsop_date'],
            '현재가': dp['stck_clpr'],
        }
        chart.append(int(dp['stck_clpr']))
        data.append(chart_data)
        mx = max(mx,int(dp['stck_hgpr']))
        mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

####주 데이터 해외####

@swagger_auto_schema(
    method='get',
    operation_id='(해외)주 별 데이터 조회',
    operation_description='일 별 데이터와 동일하게 최대 100개의 데이터 조회 가능',
    tags=['(해외)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def f_week_data(request):
    symbol = request.GET.get('symbol')
    end = request.GET.get('end') 
    broker = mojito.KoreaInvestment(
    api_key=key,
    api_secret=secret,
    acc_no=acc_no,
    exchange="나스닥",
    mock=True
    )
    resp = broker.fetch_ohlcv_overesea(
        end_day=end,
        symbol=symbol, #종목
        timeframe='W',  
        adj_price=True
    )
    daily_price = resp['output2']
    chart= []
    data=[]
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            '날짜': dp['xymd'],
            '종가': dp['clos'],
        }
        chart.append(float(dp['clos']))
        data.append(chart_data)
        mx = max(mx,float(dp['high']))
        mn = min(mn,float(dp['low']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

####분봉####
@swagger_auto_schema(
    method='get',
    operation_id='분 별 데이터 조회',
    operation_description='api호출한 시간 기준 30분전 부터의 데이터',
    tags=['주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료시간(HHMMSS 형식)', type=openapi.TYPE_STRING)
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def minute_data(request):
    print(request)
    symbol = request.GET.get('symbol')
    end = request.GET.get('end')
    result = broker._fetch_today_1m_ohlcv(symbol,end)
    daily_price = result['output2']
    jm = result['output1']['hts_kor_isnm'] ##종목
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            "종목": jm,
            '날짜': dp['stck_bsop_date'],
            '현재가': dp['stck_prpr'],
        }
        chart.append(int(dp['stck_prpr']))
        data.append(chart_data)
        mx = max(mx,int(dp['stck_hgpr']))
        mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

####해외 분봉####

@swagger_auto_schema(
    method='get',
    operation_id='(해외)분 별 데이터 조회',
    operation_description='현재 시간 기준 2시간전부터의 1분단위 데이터 입니다',
    tags=['(해외)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def f_minute_data(request):
    symbol = request.GET.get('symbol')
    print(symbol)
    headers = {
    'content-type': 'application/json',
    'authorization' : broker.access_token,
    'appkey': key,
    'appsecret': secret,
    'tr_id': 'HHDFS76950200',
    'custtype': 'P'
}
    f_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice?AUTH=&EXCD=NAS&SYMB={}&NMIN=1&PINC=0&NEXT=&NREC=120&FILL=&KEYB=".format(symbol)
    response = requests.request("GET", f_url, headers=headers, data=f_payload)
    print(f_url)
    response_data = response.json() 
    daily_price = response_data['output2']
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            '한국기준일자': dp['kymd'],
            '한국기준시간': dp['khms'],
            '종가': dp['last'],
        }
        print(chart_data)
        chart.append(float(dp['last']))
        data.append(chart_data)
        mx = max(mx,float(dp['high']))
        mn = min(mn,float(dp['low']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)


@swagger_auto_schema(
    method='get',
    operation_id='(여러번)분 별 데이터 조회',
    operation_description='(여러번)api호출한 시간 기준 30분전 부터의 데이터',
    tags=['주식 데이터'],
    manual_parameters=[
        openapi.Parameter('count', in_=openapi.IN_QUERY, description='몇 번 호출', type=openapi.TYPE_STRING),
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료시간(HHMMSS 형식)', type=openapi.TYPE_STRING)
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def repeat_minute_data(request):
    count = request.GET.get('count')
    symbol = request.GET.get('symbol')
    end = request.GET.get('end')
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for i in range (int(count)):
        here_end = str(int(end) - 30*(i))
        result = broker._fetch_today_1m_ohlcv(symbol,here_end)
        print(result)
        daily_price = result['output2']
        jm = result['output1']['hts_kor_isnm'] ##종목 ㅋㅋ
        for dp in reversed(daily_price):
            chart_data = {
                "종목": jm,
                '날짜': dp['stck_bsop_date'],
                '현재가': dp['stck_prpr'],
            }
            chart.append(int(dp['stck_prpr']))
            data.append(chart_data)
    mx = max(mx,int(dp['stck_hgpr']))
    mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)


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
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([permissions.AllowAny])
def data_to_sound(request):
    data = request.data.get('lista')
    duration = 0.5
    result = generate_sine_wave(0.1, 0)  # 사인파들을 numpy.ndarray 형태로 받아올 빈 numpy.ndarray
    for i in data:
        sine = generate_sine_wave(duration, i)
        result = np.concatenate((result, sine))

    wav_stream = BytesIO()
    wavfile.write(wav_stream, 44100, result)
    wav_bytes = wav_stream.getvalue()

    # 음성파일을 Response 객체로 전달하며, content_type은 'audio/wav'로 설정
    return HttpResponse(wav_bytes, content_type='audio/wav')
# @swagger_auto_schema(
#     method='post',
#     operation_id='data_to_sound',
#     operation_description='데이터를 소리로 변환',
#     tags=['sound'],
#     request_body=Schema(
#         type=TYPE_ARRAY,
#         items=Schema(
#             type=TYPE_NUMBER,
#         ),
#     ),
# )
# @api_view(['POST'])
# @authentication_classes([SessionAuthentication, BasicAuthentication])
# @permission_classes([permissions.AllowAny])
# def data_to_sound(request):
#     data = request.data.get('lista')
#     duration = 0.5
#     result = generate_sine_wave(0.1,0) # 사인파들을 numpy.ndarray 형태로 받아올 빈 numpy.ndarray
#     for i in data:  # 실험용 , 주가데이터를 알맞게 변환해서 넣어야 함
#         sine = generate_sine_wave(duration, i) # 사인파로 만들고
#         result = np.concatenate((result,sine)) # 만든 것들을 result에 합침
#     wav_stream = BytesIO()
#     wavfile.write(wav_stream, 44100, result)
#     response = HttpResponse(wav_stream.getvalue(), content_type='audio/wav')
#     response['Content-Disposition'] = 'attachment; filename="Sine.wav"'
#     return response

##############################################################################################################

@swagger_auto_schema(
    method='get',
    operation_id='사용자의 정보 조회',
    operation_description='보유한 종목/기록 등',
    tags=['내정보'],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def my_stocks(request):
    try:
        user = request.user
        user_records = user.records.all()
        user_stock = UserStock.objects.get(user=user)
        user_stock_data = UserStockSerializer(user_stock).data
        record_data = RecordSerializer(user_records, many=True).data
        return Response({'user_stock_data' : user_stock_data , 'record_data' : record_data})
    except User.DoesNotExist:
        return Response({'error': '없는 유저입니다'}, status=404)

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
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def sell(request):
    stock_symbol = request.data.get('stock_symbol')
    quantity = request.data.get('quantity')
    resp = broker.fetch_price(stock_symbol)
    to_price = int(resp['output']['stck_prpr'])*quantity
    user = request.user
    try:
        stock = Stock.objects.get(symbol=stock_symbol)
    except Stock.DoesNotExist:
        return Response({"error": "없는 종목입니다"}, status=400)
    try:
        user_stock = UserStock.objects.get(user=user, stock=stock)
    except UserStock.DoesNotExist:
        return Response({"error": "해당 종목을 보유하고 있지 않습니다"}, status=400)

    if to_price <= user_stock.price:
        user.user_property += to_price
        user_stock.price -= to_price
        user.save()
    else:
        return Response({"error": "종목 보유량보다 큰 값을 입력 받았습니다"}, status=400)
    user_stock.having_quantity -= quantity
    user_stock.save()
    if user_stock.having_quantity <=0:
        user_stock.delete()

    record = Record.objects.create(
        user = user,
        stock = stock,
        transaction_type = '판매',
        quantity = quantity,
        price = to_price,
        left_money = user.user_property + to_price
    )
    stock_data = StockSerializer(stock).data
    user_stock_data = UserStockSerializer(user_stock).data
    record_data = RecordSerializer(record).data
    return Response({"message": "판매완료","stock": stock_data,"user_stock": user_stock_data, "record": record_data}, status=200)

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
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def buy(request):
    stock_symbol = request.data.get('stock_symbol')
    quantity = request.data.get('quantity')
    resp = broker.fetch_price(stock_symbol)
    to_price = int(resp['output']['stck_prpr'])*quantity

    user = request.user

    try:
        stock = Stock.objects.get(symbol=stock_symbol)
    except Stock.DoesNotExist:
        return Response({"error": "없는 종목입니다"}, status=400)

    if user.user_property >= to_price:
        user.user_property -= to_price
        user.save()
    else:
        return Response({"error":"돈이 부족합니다"}, status=400)
    try:
        user_stock = UserStock.objects.get(user=user, stock=stock)
        user_stock.price += to_price
        user_stock.having_quantity += quantity
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
            'stock_name': openapi.Schema(type=openapi.TYPE_STRING),
        },
        required=['stock_name']
    )
)
@api_view(['POST'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def like_stock(request):
    stock_name = request.data.get('stock_name')
    try:
        stock = Stock.objects.get(name=stock_name)
    except Stock.DoesNotExist:
        return Response(status=404)

    user = request.user
    user.liked_stock.add(user)  
    stock.likes += 1
    stock.save()
    s = StockSerializer

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
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([permissions.AllowAny])
def data_to_sound(request):
    data = request.data.get('lista')
    duration = 0.5
    result = generate_sine_wave(0.1, 0)  # 사인파들을 numpy.ndarray 형태로 받아올 빈 numpy.ndarray
    for i in data:
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
    def get(request):
        # user, _ = JWTAuthentication().authenticate(request) # 이게 안되면 check_jwt_user를 통해 user정보를 받아서 user_id를 사용하기
        user = User.objects.get(id = 2)
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
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([permissions.AllowAny])
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
