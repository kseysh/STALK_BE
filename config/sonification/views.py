from django.db import IntegrityError
import requests
import mojito
import numpy as np

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
from .serializers import StockSerializer, RecordSerializer, UserStockSerializer

from accounts.models import User
from .models import Stock, Record, UserStock

##한국투자증권 keys
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

#실전모의계좌용 api 공용
payload = {}
f_payload = ""

##################DRF####################

####거래량 순위####
# @swagger_auto_schema(
#     method='get',
#     operation_id='거래량 순위(30개)',
#     operation_description='거래량 순위(30개)',
#     tags=['주식 데이터']
# )
# @api_view(['GET'])
# @authentication_classes([SessionAuthentication,BasicAuthentication])
# @permission_classes([permissions.AllowAny])
# def transaction_rank(request):
#     headers = {
#         'content-type': 'application/json',
#         'authorization' : broker.access_token,
#         'appkey': key,
#         'appsecret': secret,
#         'tr_id': 'FHPST01710000',
#         'custtype': 'P'
#     }
#     url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/volume-rank?FID_COND_MRKT_DIV_CODE=J&FID_COND_SCR_DIV_CODE=20171&FID_INPUT_ISCD=0002&FID_DIV_CLS_CODE=0&FID_BLNG_CLS_CODE=0&FID_TRGT_CLS_CODE=111111111&FID_TRGT_EXLS_CLS_CODE=000000&FID_INPUT_PRICE_1=0&FID_INPUT_PRICE_2=0&FID_VOL_CNT=0&FID_INPUT_DATE_1=0"
#     response = requests.get(url, headers=headers)
#     response_data = response.json() 
#     transaction_data_list = []
#     for item in response_data['output']:
#         data = {
#             '종목명': item['hts_kor_isnm'],
#             '종목코드': item['mksc_shrn_iscd'],
#             '거래량 순위': item['data_rank'],
#             '현재가': item['stck_prpr'],
#             '전일 대비율': item['prdy_ctrt'],
#             '누적 거래량': item['acml_vol'],# 1일 거래량 입니다
#         }
#         try:
#             stock, created = Stock.objects.get_or_create(
#             symbol=item['mksc_shrn_iscd'],
#             name=item['hts_kor_isnm'],
#             likes=0,
#             )
#             if created:
#                 transaction_data_list.append(data)
#             else: 
#                 transaction_data_list.append(data)
#         except IntegrityError:
#             pass

#     return Response({'거래량 순위': transaction_data_list})

####해외주식 시가총액 기준####

@swagger_auto_schema(
    method='get',
    operation_id='(해외)시가총액기준 정렬(100개)',
    operation_description='(해외)시가총액기준 정렬(100개)',
    tags=['(해외)주식 데이터']
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def f_transaction_rank(request):
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
    transaction_data_list = []
    for item in response_data['output2']:
        data = {
            '종목명': item['name'],
            '종목코드': item['symb'],
            '시가총액 순위': item['rank'],
            '시가총액' : float(item['valx']),
            '현재가': float(item['last']),
            '전일 대비율': float(item['rate']),
            '대비': float(item['diff']),
        }
        try:
            stock, created = Stock.objects.get_or_create(
            symbol=item['symb'],
            name=item['name'],
            likes=0,
            )
            if created:
                like=0
                data['좋아요 개수'] = like
                transaction_data_list.append(data)
            else: 
                like=stock.likes
                data['좋아요 개수'] = like
                transaction_data_list.append(data)
        except IntegrityError:
            like=stock.likes
            data['좋아요 개수'] = like
            pass

    return Response({'시가총액 순위': transaction_data_list})

####국내주식 시가총액 기준####
@swagger_auto_schema(
    method='get',
    operation_id='시가총액기준 정렬(100개)',
    operation_description= '시가총액기준 정렬(100개)',
    tags=['주식 데이터']
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def transaction_rank(request):
    headers = {
        'content-type': 'application/json',
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
        try:
            stock, created = Stock.objects.get_or_create(
            symbol=item['code'],
            name=item['name'],
            likes=0,
            )
            if created:
                like=0
                data['좋아요 개수'] = like
                transaction_data_list.append(data)
            else: 
                like=stock.likes
                data['좋아요 개수'] = like
                transaction_data_list.append(data)
        except IntegrityError:
            like=stock.likes
            data['좋아요 개수'] = like
            pass

    return Response({'시가총액 순위': transaction_data_list})

####호출기준 현재가####
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
    resp = broker.fetch_price(symbol)
    print(resp)
    chart_data = { 
        '전일대비부호': resp['output']['prdy_vrss_sign'],
        '전일 대비율': resp['output']['prdy_ctrt'],
        '누적 거래량': resp['output']['acml_vol'],
        'HTS 시가총액': resp['output']['hts_avls'],
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

####일 데이터####
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
        start_day=begin, #YYYYMMDD 
        end_day=end,
        symbol=symbol, 
        timeframe='D',  
        adj_price=True
    )
    daily_price = resp['output2']
    jm = resp['output1']['hts_kor_isnm']
    sc = resp['output1']['hts_avls']
    hj = resp['output1']['stck_prpr']
    dby = resp['output1']['prdy_ctrt']
    chart= []
    data=[]
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            "종목": jm,
            "전일 대비율": dby,
            "누적 거래량" : dp['acml_vol'],
            "시가총액" : sc,
            '날짜': dp['stck_bsop_date'],
            '종가': dp['stck_clpr'],
            '시가': dp['stck_oprc'],
            '현재가': hj,
            '고가': dp['stck_hgpr'],
            '저가': dp['stck_lwpr'],
        }
        chart.append(int(dp['stck_clpr']))
        data.append(chart_data)
        mx = max(mx,int(dp['stck_hgpr']))
        mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

####업종 날짜별####
@swagger_auto_schema(
    method='get',
    operation_id='날짜 별 데이터 조회+ 현재 업종 데이터 가능',
    operation_description='최대 50일 조회가능/ 시작일~종료일 + 현재 업종 데이터 보고 싶으면 하루만 조회해서 보세요',
    tags=['(업종)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='업종코드(코스피:0001, 코스닥:1001)', type=openapi.TYPE_STRING),
        openapi.Parameter('start', in_=openapi.IN_QUERY, description='시작일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def a_day_data(request):
    symbol = request.GET.get('symbol')
    start = request.GET.get('start')
    end = request.GET.get('end')
    headers = {
        'content-type': 'application/json',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'FHKUP03500100'
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice?fid_cond_mrkt_div_code=U&fid_input_iscd={}&fid_input_date_1={}&fid_input_date_2={}&fid_period_div_code=D".format(symbol, start, end)

    response = requests.request("GET", url, headers=headers, data=payload)
    response_data = response.json() 
    jm = response_data['output1']['hts_kor_isnm']
    now_jm = response_data['output1']['bstp_nmix_prpr']
    dby = response_data['output1']['bstp_nmix_prdy_ctrt']
    daily_price = response_data['output2']
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            '업종' : jm,
            '전일 대비율' : dby,
            '일자': dp['stck_bsop_date'],
            '시가': dp['bstp_nmix_oprc'],
            '호출시간 현재가': now_jm,
            '해당일 업종 현재가': dp['bstp_nmix_prpr'],
            '해당일 업종 고가': dp['bstp_nmix_hgpr'],
            '해당일 업종 저가': dp['bstp_nmix_lwpr'],
        }
        chart.append(float(dp['bstp_nmix_prpr']))
        data.append(chart_data)
        mx = max(mx,float(dp['bstp_nmix_hgpr']))
        mn = min(mn,float(dp['bstp_nmix_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

####해외 업종 날짜별####
@swagger_auto_schema(
    method='get',
    operation_id='(해외)날짜 별 데이터 조회+ 현재 업종 데이터 가능',
    operation_description='최대 50일 조회가능/ 시작일~종료일 + 현재 업종 데이터 보고 싶으면 하루만 조회해서 보세요',
    tags=['(해외)(업종)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='업종코드(S&P500 : SPX, 나스닥100:NDX)', type=openapi.TYPE_STRING),
        openapi.Parameter('start', in_=openapi.IN_QUERY, description='시작일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def f_a_day_data(request):
    symbol = request.GET.get('symbol')
    start = request.GET.get('start')
    end = request.GET.get('end')
    payload=""
    headers = {
        'content-type': 'application/json',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'FHKST03030100',
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-daily-chartprice?FID_COND_MRKT_DIV_CODE=N&FID_INPUT_ISCD={}&FID_INPUT_DATE_1={}&FID_INPUT_DATE_2={}&FID_PERIOD_DIV_CODE=D".format(symbol, start, end)

    response = requests.request("GET", url, headers=headers, data=payload)
    response_data = response.json() 
    jm = response_data['output1']['hts_kor_isnm']
    now_jm = response_data['output1']['ovrs_nmix_prpr']
    jg = response_data['output1']['ovrs_nmix_prdy_clpr']
    daily_price = response_data['output2']
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            '업종' : jm,
            '일자': dp['stck_bsop_date'],
            '시가': dp['ovrs_nmix_oprc'],
            '전일종가': jg,
            '호출시간 현재가': now_jm,
            '해당일 업종 현재가': dp['ovrs_nmix_prpr'],
            '해당일 업종 고가': dp['ovrs_nmix_hgpr'],
            '해당일 업종 저가': dp['ovrs_nmix_lwpr'],
        }
        print(chart_data)
        chart.append(float(dp['ovrs_nmix_prpr']))
        data.append(chart_data)
        mx = max(mx,float(dp['ovrs_nmix_hgpr']))
        mn = min(mn,float(dp['ovrs_nmix_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

####해외 종목 데이터 날짜별 ####
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
    exchange="나스닥",  ##나스닥으로 설정
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
            '시가': dp['open'],
            '고가': dp['high'],
            '저가': dp['low'],
            '거래량': dp['tvol'],
        }
        chart.append(float(dp['clos']))
        data.append(chart_data)
        mx = max(mx,float(dp['high']))
        mn = min(mn,float(dp['low']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

################################WEEK#####################################

####국내 종목 주 데이터####
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
    resp = broker.fetch_ohlcv(
        start_day=begin, #YYYYMMDD
        end_day=end,
        symbol=symbol, 
        timeframe='W',  
        adj_price=True
    )
    daily_price = resp['output2']
    print(daily_price)
    jm = resp['output1']['hts_kor_isnm']
    sc = resp['output1']['hts_avls']
    hj = resp['output1']['stck_prpr']
    dby = resp['output1']['prdy_ctrt']
    chart= []
    data=[]
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            "종목": jm,
            "전일 대비율": dby,
            "누적 거래량" : dp['acml_vol'],
            "시가총액" : sc,
            '날짜': dp['stck_bsop_date'],
            '현재가': hj,
            '시가' : dp['stck_oprc'],
            '종가' : dp['stck_clpr'],
            '고가': dp['stck_hgpr'],
            '저가': dp['stck_lwpr'],
        }
        chart.append(int(dp['stck_clpr']))
        data.append(chart_data)
        mx = max(mx,int(dp['stck_hgpr']))
        mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

####국내 주 데이터 업종####
@swagger_auto_schema(
    method='get',
    operation_id='날짜 별 데이터 조회+ 현재 업종 데이터 가능',
    operation_description='최대 50일 조회가능/ 시작일~종료일 + 현재 업종 데이터 보고 싶으면 하루만 조회해서 보세요',
    tags=['(업종)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='업종코드(코스피:0001, 코스닥:1001)', type=openapi.TYPE_STRING),
        openapi.Parameter('start', in_=openapi.IN_QUERY, description='시작일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def a_week_data(request):
    symbol = request.GET.get('symbol')
    start = request.GET.get('start')
    end = request.GET.get('end')
    headers = {
        'content-type': 'application/json',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'FHKUP03500100',
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice?fid_cond_mrkt_div_code=U&fid_input_iscd={}&fid_input_date_1={}&fid_input_date_2={}&fid_period_div_code=W".format(symbol, start, end)

    response = requests.request("GET", url, headers=headers, data=payload)
    response_data = response.json() 
    jm = response_data['output1']['hts_kor_isnm']
    now_jm = response_data['output1']['bstp_nmix_prpr']
    dby = response_data['output1']['bstp_nmix_prdy_ctrt']
    daily_price = response_data['output2']
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            '업종' : jm,
            '대비율' : dby,
            '일자': dp['stck_bsop_date'],
            '시가': dp['bstp_nmix_oprc'],
            '호출시간 현재가': now_jm,
            '해당일 업종 현재가': dp['bstp_nmix_prpr'],
            '해당일 업종 최고가': dp['bstp_nmix_hgpr'],
            '해당일 업종 최저가': dp['bstp_nmix_lwpr'],
        }
        chart.append(float(dp['bstp_nmix_prpr']))
        data.append(chart_data)
        mx = max(mx,float(dp['bstp_nmix_hgpr']))
        mn = min(mn,float(dp['bstp_nmix_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

#### 주 해외 업종####
@swagger_auto_schema(
    method='get',
    operation_id='(해외)주 별 데이터 조회+ 현재 업종 데이터 가능',
    operation_description='최대 100개 조회가능/ 시작일~종료일 + 현재 업종 데이터 보고 싶으면 하루만 조회해서 보세요',
    tags=['(해외)(업종)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='업종코드(S&P500 : SPX,나스닥100:NDX)', type=openapi.TYPE_STRING),
        openapi.Parameter('start', in_=openapi.IN_QUERY, description='시작일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
        openapi.Parameter('end', in_=openapi.IN_QUERY, description='종료일(YYYYMMDD 형식)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def f_a_week_data(request):
    symbol = request.GET.get('symbol')
    start = request.GET.get('start')
    end = request.GET.get('end')
    payload=""
    headers = {
        'content-type': 'application/json',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'FHKST03030100'
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-daily-chartprice?FID_COND_MRKT_DIV_CODE=N&FID_INPUT_ISCD={}&FID_INPUT_DATE_1={}&FID_INPUT_DATE_2={}&FID_PERIOD_DIV_CODE=W".format(symbol,start,end)
    response = requests.request("GET", url, headers=headers, data=payload)
    response_data = response.json() 
    print(response_data)
    now_jm = response_data['output1']['ovrs_nmix_prpr']
    print(now_jm)
    jm = response_data['output1']['hts_kor_isnm']
    jg = response_data['output1']['ovrs_nmix_prdy_clpr']
    daily_price = response_data['output2']
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            '업종' : jm,
            '일자': dp['stck_bsop_date'],
            '시가': dp['ovrs_nmix_oprc'],
            '전일종가': jg,
            '호출시간 현재가': now_jm,
            '해당일 업종 현재가': dp['ovrs_nmix_prpr'],
            '해당일 업종 고가': dp['ovrs_nmix_hgpr'],
            '해당일 업종 저가': dp['ovrs_nmix_lwpr'],
        }
        print(chart_data)
        chart.append(float(dp['ovrs_nmix_prpr']))
        data.append(chart_data)
        mx = max(mx,float(dp['ovrs_nmix_hgpr']))
        mn = min(mn,float(dp['ovrs_nmix_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

####주 단위 종목 데이터 해외####
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
            '시가': dp['open'],
            '등락율': dp['rate'],
            '거래량': dp['tvol'],
            '최고가': dp['high'],
            '최저가': dp['low'],
        }
        chart.append(float(dp['clos']))
        data.append(chart_data)
        mx = max(mx,float(dp['high']))
        mn = min(mn,float(dp['low']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

#################################MINUTE#################################

####원래분봉####
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
def hmm__minute_data(request):
    print(request)
    symbol = request.GET.get('symbol')
    end = request.GET.get('end')
    result = broker._fetch_today_1m_ohlcv(symbol,end)
    daily_price = result['output2']
    jm = result['output1']['hts_kor_isnm'] ##종목
    dby = result['output1']['prdy_ctrt']
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
            '저가': dp['stck_lwpr'],
            '전일대비율': dby,
        }
        
        chart.append(int(dp['stck_prpr']))
        data.append(chart_data)
        mx = max(mx,int(dp['stck_hgpr']))
        mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)


####국내 종목 분 데이터####
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
def minute_data(request):
    count = request.GET.get('count')
    symbol = request.GET.get('symbol')
    end = request.GET.get('end')
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for i in range (int(count)):
        here_end = str(int(end) - 30*(i))
        result = broker._fetch_today_1m_ohlcv(symbol,here_end)
        daily_price = result['output2']
        jm = result['output1']['hts_kor_isnm'] 
        nj = result['output1']['acml_vol'] 
        dby = result['output1']['prdy_ctrt']
        for dp in reversed(daily_price):
            chart_data = {
                "종목": jm,
                "누적 거래량" : nj,
                "전일 대비율" : dby,
                '날짜': dp['stck_bsop_date'],
                '현재가': dp['stck_prpr'],
                '시가': dp['stck_hgpr'],
                '저가': dp['stck_lwpr'],
            }
            chart.append(int(dp['stck_prpr']))
            data.append(chart_data)
    mx = max(mx,int(dp['stck_hgpr']))
    mn = min(mn,int(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

####국내 업종 분 데이터####
@swagger_auto_schema(
    method='get',
    operation_id='(업종)분 별 데이터 조회',
    operation_description='api호출한 시간 기준 30분전 부터의 데이터',
    tags=['(업종)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='업종코드(코스피:0001, 코스닥:1001)', type=openapi.TYPE_STRING),
        openapi.Parameter('sec', in_=openapi.IN_QUERY, description='분단위(60 이면 1분단위 120이면 2분단위', type=openapi.TYPE_STRING)
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def a_minute_data(request):
    print(request)
    symbol = request.GET.get('symbol')
    sec = request.GET.get('sec')
    result = broker.a_fetch_today_1m_ohlcv(symbol,sec)
    daily_price = result['output2']
    jm = result['output1']['hts_kor_isnm'] ##종목
    gr = result['output1']['acml_vol'] ##종목
    chart= [] 
    data= []
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            "종목": jm,
            "거래량": gr,
            '날짜': dp['stck_bsop_date'],
            '현재가': dp['stck_prpr'],
            '시가': dp['stck_oprc'],
            '고가': dp['stck_hgpr'],
            '저가': dp['stck_lwpr'],
        }
        chart.append(float(dp['stck_prpr']))
        data.append(chart_data)
        mx = max(mx,float(dp['stck_hgpr']))
        mn = min(mn,float(dp['stck_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

####해외 업종 분 데이터####
@swagger_auto_schema(
    method='get',
    operation_id='(해외)분 별 데이터 조회',
    operation_description='최근 102건 조회가능',
    tags=['(해외)(업종)주식 데이터'],
    manual_parameters=[
        openapi.Parameter('symbol', in_=openapi.IN_QUERY, description='업종코드(S&P500 : SPX,나스닥100:NDX)', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def f_a_minute_data(request):
    symbol = request.GET.get('symbol')
    payload=""
    headers = {
        'content-type': 'application/json',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'FHKST03030200',
        'custtype': 'P'
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice?FID_COND_MRKT_DIV_CODE=N&FID_INPUT_ISCD={}&FID_HOUR_CLS_CODE=0&FID_PW_DATA_INCU_YN=Y".format(symbol)

    response = requests.request("GET", url, headers=headers, data=payload)
    response_data = response.json() 
    jm = response_data['output1']['hts_kor_isnm']
    gr = response_data['output1']['acml_vol']
    daily_price = response_data['output2']
    chart= []
    data= []
    mx = 0 ; mn = 0
    for dp in reversed(daily_price):
        chart_data = {
            '업종' : jm,
            '일자': dp['stck_bsop_date'],
            '거래량': gr,
            '해당일 업종 현재가': dp['optn_prpr'],
            '해당일 업종 시가': dp['optn_oprc'],
            '해당일 업종 고가': dp['optn_hgpr'],
            '해당일 업종 저가': dp['optn_lwpr'],
        }
        print(chart_data)
        chart.append(float(dp['optn_prpr']))
        data.append(chart_data)
        mx = max(mx,float(dp['optn_hgpr']))
        mn = min(mn,float(dp['optn_lwpr']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

####해외 종목 분 데이터####
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
    headers = {
        'content-type': 'application/json',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'HHDFS76950200',
        'custtype': 'P'
    }
    f_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice?AUTH=&EXCD=NAS&SYMB={}&NMIN=1&PINC=1&NEXT=&NREC=120&FILL=&KEYB=".format(symbol)

    response = requests.request("GET", f_url, headers=headers, data=f_payload)
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
            '시가': dp['open'],
            '고가': dp['high'],
            '저가': dp['low'],
        }
        chart.append(float(dp['last']))
        data.append(chart_data)
        mx = max(mx,float(dp['high']))
        mn = min(mn,float(dp['low']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=False)

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
    headers = {
        'content-type': 'application/json',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'HHDFS76200200',
    }
    f_url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price-detail?AUTH=&EXCD=NAS&SYMB={}".format(symbol)

    response = requests.request("GET", f_url, headers=headers, data=f_payload)
    response_data = response.json() 
    daily_price = response_data['output'] 
    chart_data = {
        '거래량' : daily_price['tvol'],
        '전일종가': daily_price['base'],
        '현재가': daily_price['last'],
        '고가': daily_price['high'],
        '저가': daily_price['low'],
        '시가': daily_price['open'],
        '시가총액': daily_price['tomv'],
        '등락율': daily_price['t_xrat'],
    }
    stock = Stock.objects.get(symbol=symbol)
    user_stock = UserStock.objects.filter(stock=stock)

    if user_stock is not None:
        for user_stock in user_stock:
            if user_stock.having_quantity >= 1:
                now_stock_price=int(response_data['output']['last']) * user_stock.having_quantity
                user_stock.profit_loss = user_stock.price - now_stock_price
                user_stock.now_price = now_stock_price
                user_stock.rate_profit_loss=(now_stock_price-user_stock.price)/user_stock.price*100
                user_stock.save()
    else:
        pass
    return JsonResponse({'chart_data': chart_data}, safe=False)

###############################TRANSACTION#################################

####유저 정보####
@swagger_auto_schema(
    method='get',
    operation_id='사용자의 정보 조회',
    operation_description='보유한 종목/기록 등',
    tags=['내정보'],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def user_info(request):
    try:
        # user = request.user
        user = User.objects.get(id=2)
        user_liked_stocks = Stock.objects.filter(liked_user=user)
        liked_stock_names = [stock.name for stock in user_liked_stocks]
        try:
            user_stock = UserStock.objects.get(user=user)
            user_stock_data = UserStockSerializer(user_stock).data
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
        
        return Response({'유저정보': user_data,'찜한목록': liked_stock_names,'모의투자한 종목' : user_stock_data , '거래 기록' : record_data})
    
    except User.DoesNotExist:
        return Response({'error': '로그인 하세요.'}, status=404)

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
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def sell(request):
    stock_symbol = request.data.get('stock_symbol')
    quantity = request.data.get('quantity')
    resp = broker.fetch_price(stock_symbol)
    to_price = int(resp['output']['stck_prpr'])*quantity
    # user = request.user
    user = User.objects.get(id=2)
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
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def buy(request):
    stock_symbol = request.data.get('stock_symbol')
    quantity = request.data.get('quantity')
    resp = broker.fetch_price(stock_symbol)
    to_price = int(resp['output']['stck_prpr'])*quantity

    # user = request.user
    user = User.objects.get(id=2)
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
            'symbol': openapi.Schema(type=openapi.TYPE_STRING),
        },
        required=['symbol']
    )
)
@api_view(['POST'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def like_stock(request):
    stock_symbol = request.data.get('symbol')
    try:
        stock = Stock.objects.get(symbol=stock_symbol)
    except Stock.DoesNotExist:
        return Response(status=404)

    # user = request.user
    user = User.objects.get(id=2)
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
    stock_name= openapi.Parameter('stock_name', openapi.IN_QUERY, description='stock_name', required=True, type=openapi.TYPE_STRING)
    @swagger_auto_schema(tags=['좋아요가 눌려져 있는 주식인지 확인하는 기능'],manual_parameters=[stock_name], responses={200: 'Success'})
    def get(request):
        user, _ = JWTAuthentication().authenticate(request) # 이게 안되면 check_jwt_user를 통해 user정보를 받아서 user_id를 사용하기
        stock_name = request.GET.get("stock_name")
        stock = Stock.objects.get(stock_name=stock_name)
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
        
    ID = "qcxc89t0bs" 
        
    headers = {
        "Content-Type": "application/octet-stream", # Fix
        "X-NCP-APIGW-API-KEY-ID": ID,
        "X-NCP-APIGW-API-KEY": sound_secret,
    }
    audio_file = request.FILES.get('audio')

    response = requests.post(URL, data=audio_file.read(), headers=headers)
    rescode = response.status_code
    if rescode == 200:
        return Response(response.text)
    
