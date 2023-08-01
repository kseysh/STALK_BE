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

#그냥 현재가
@swagger_auto_schema(
    method='get',
    operation_id='현재 주가 확인 및 사용자 투자종목 업데이트',
    operation_description='현재 주가 확인 및 사용자 투자종목 업데이트',
    tags=['DATA'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
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
    user_stock = UserStock.objects.get(stock=stock)
    stock.profit_loss = resp['output']['stck_prpr']*user_stock.having_qunatitiy - user_stock.price
    user_stock.save()
    return JsonResponse({'chart_data': chart_data}, safe=True)

####일봉####
@swagger_auto_schema(
    method='get',
    operation_id='일봉 조회',
    operation_description='일봉 데이터를 조회합니다',
    tags=['DATA'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
        openapi.Parameter('begin', in_=openapi.IN_QUERY, description='시작일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def il_bong(request):
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
            '시가': dp['stck_oprc'],
            '현재가': dp['stck_clpr'],
            '고가': dp['stck_hgpr'],
            '저가': dp['stck_lwpr']
        }
        chart.append(int(dp['stck_clpr']))
        data.append(chart_data)
        mx = max(mx,int(dp['stck_hgpr']))
        mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

#분봉 (30분전 까지 탐색)
# @swagger_auto_schema(
#     method='get',
#     operation_id='일봉 조회',
#     operation_description='일봉 데이터를 조회합니다',
#     tags=['DATA'],
#     manual_parameters=[
#         openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
#         openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
#     ],
# )

####분봉####
@swagger_auto_schema(
    method='get',
    operation_id='분봉 조회',
    operation_description='분봉 데이터를 조회합니다',
    tags=['DATA'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='종목코드', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료시간(HHMMSS 형식)', type=openapi.TYPE_STRING)
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def boon_bong(request):
    print(request)
    symbol = request.GET.get('symbol')
    end = request.GET.get('end')
    result = broker._fetch_today_1m_ohlcv(symbol,end)
    daily_price = result['output2']
    jm = result['output1']['hts_kor_isnm'] ##종목 ㅋㅋ
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            "종목": jm,
            '날짜': dp['stck_bsop_date'],
            '시가': dp['stck_oprc'],
            '현재가': dp['stck_prpr'],
            '고가': dp['stck_hgpr'],
            '저가': dp['stck_lwpr']
        }
        chart.append(int(dp['stck_prpr']))
        data.append(chart_data)
        mx = max(mx,int(dp['stck_hgpr']))
        mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

####차트 음향화####

@api_view(['POST'])
def data_to_sound(request):
    data = request.data.get('lista')
    duration = 0.5
    result = generate_sine_wave(0.1,0) # 사인파들을 numpy.ndarray 형태로 받아올 빈 numpy.ndarray
    for i in data:  # 실험용 , 주가데이터를 알맞게 변환해서 넣어야 함
        sine = generate_sine_wave(duration, i) # 사인파로 만들고
        result = np.concatenate((result,sine)) # 만든 것들을 result에 합침
    wav_stream = BytesIO()
    wavfile.write(wav_stream, 44100, result)
    response = HttpResponse(wav_stream.getvalue(), content_type='audio/wav')
    response['Content-Disposition'] = 'attachment; filename="Sine.wav"'
    return response

##############################################################################################################

@api_view(['GET'])
def my_stocks(request):
    try:
        user = request.user
        user_stocks = user.stocks.all()
        user_records = user.records.all()
        user_stock = UserStock.objects.get(user=user, stock=user_stocks)
        stock_data = StockSerializer(user_stocks, many=True).data
        record_data = RecordSerializer(user_records, many=True)
        user_stock_data = RecordSerializer(user_stock, many=True)
        return Response({'stock_data' : stock_data , 'record_data' : record_data, 'user_stock_data' : user_stock_data})
    except User.DoesNotExist:
        return Response({'error': '없는 유저입니다'}, status=404)


@swagger_auto_schema(
    method='post',
    operation_id='매도',
    operation_description='매도하기',
    tags=['transaction'],
)
@api_view(['POST'])
def sell(request):
    stock_symbol = request.data.get('stock_symbol')
    quantity = request.data.get('quantity')
    resp = broker.fetch_price(stock_symbol)
    to_price = int(resp['output']['stck_prpr'])*quantity
    # user = request.user

    ##### 로그인 구현전이라 ######

    user_id = request.data.get('user_id')
    user = User.objects.get(pk=user_id)

    try:
        stock = Stock.objects.get(symbol=stock_symbol)
    except Stock.DoesNotExist:
        return Response({"error": "없는 종목입니다"}, status=400)
    
    user_stock = UserStock.objects.get(user=user, stock=stock)
    if to_price <= user_stock.price:
        user.user_property += to_price
        user_stock.price -= to_price
        user.save()
    user_stock.having_quantity -= quantity
    user_stock.save()

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
    tags=['transaction'],
)
@api_view(['POST'])
def buy(request):
    stock_symbol = request.data.get('stock_symbol')
    quantity = request.data.get('quantity')
    resp = broker.fetch_price(stock_symbol)
    to_price = int(resp['output']['stck_prpr'])*quantity
    # user = request.user

    ##### 로그인 구현전이라 ######

    user_id = request.data.get('user_id')
    user = User.objects.get(pk=user_id)

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
        stock=stock,
        having_quantity=quantity,
        profit_loss=0
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