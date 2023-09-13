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
from django.http import HttpResponse, JsonResponse

from accounts.views import check_jwt
from transaction.serializers import StockSerializer, RecordSerializer, UserStockSerializer

from accounts.models import User
from transaction.models import PurchaseHistory, Stock, Record, UserStock

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

f_payload = {}

#값의 변화량을 주파수로 치환하는 함수
def substitution(mx,mn,chart):
    lista = []
    for i in chart:        
        percentage = ((i - mn)/((mx-mn))) *200
        lista.append(percentage*10-200)
    return lista

#사인파 만드는 함수
def generate_sine_wave(duration, frequency, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    data = 0.5 * np.sin(2 * np.pi * frequency * t)
    scaled_data = (data * 32767).astype(np.int16)
    return scaled_data


@swagger_auto_schema(
    method='get',
    operation_id='(해외)시가총액기준 정렬(100개)',
    operation_description='(해외)시가총액기준 정렬(100개)',
    tags=['(해외)주식 데이터']
)
@api_view(['GET'])
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
    exchange_rate = get_exchange_rate(request)
    
    for item in response_data['output2']:
        image_path = os.path.join(settings.MEDIA_ROOT, f'{item["symb"]}.jpg')
        if os.path.isfile(image_path):
            image_url = f'https://stalksound.store/image/{item["symb"]}.jpg'
        else:
            image_url = 'https://stalksound.store/image/default.jpg'
        data = {
            '종목명': item['name'],
            '종목코드': item['symb'],
            '시가총액 순위': item['rank'],
            '시가총액' : float(item['valx']),
            '$현재가': float(item['last']),
            '현재가': int(float(item['last'])*float(exchange_rate)),
            '전일 대비율': float(item['rate']),
            '대비': float(item['diff']),
            '환율':exchange_rate,
            '이미지URL': image_url
        }
        try:
            stock = Stock.objects.get(
            symbol=item['symb'],
            name=item['name'],
            )
            like=stock.likes
            data['좋아요 개수'] = like
            transaction_data_list.append(data)
        except ObjectDoesNotExist:
            try:
                stock = Stock.objects.create(
                symbol=item['symb'],
                name=item['name'],
                is_domestic_stock = False,
                stock_image=f'{item["symb"]}.jpg'
                )
                data['좋아요 개수'] = 0
                transaction_data_list.append(data)
            except:
                pass
        

    return Response({'시가총액 순위': transaction_data_list})

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
    exchange_rate = get_exchange_rate(request)
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
            '환율':exchange_rate,
        }
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
    exchange_rate = get_exchange_rate(request)
    for dp in reversed(daily_price):
        chart_data = {
            '날짜': dp['xymd'],
            '종가': dp['clos'],
            '시가': dp['open'],
            '고가': dp['high'],
            '저가': dp['low'],
            '거래량': dp['tvol'],
            '환율':exchange_rate,
        }
        chart.append(float(dp['clos']))
        data.append(chart_data)
        mx = max(mx,float(dp['high']))
        mn = min(mn,float(dp['low']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

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
    exchange_rate = get_exchange_rate(request)
    for dp in reversed(daily_price):
        chart_data = {
            '날짜': dp['xymd'],
            '종가': dp['clos'],
            '시가': dp['open'],
            '등락율': dp['rate'],
            '거래량': dp['tvol'],
            '최고가': dp['high'],
            '최저가': dp['low'],
            '환율':exchange_rate,
        }
        chart.append(float(dp['clos']))
        data.append(chart_data)
        mx = max(mx,float(dp['high']))
        mn = min(mn,float(dp['low']))
    lista = substitution(mx,mn,chart)
    return JsonResponse({'data': data, 'lista': lista}, safe=True)

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
    exchange_rate = get_exchange_rate(request)
    for dp in reversed(daily_price):
        chart_data = {
            '업종' : jm,
            '일자': dp['stck_bsop_date'],
            '거래량': gr,
            '해당일 업종 현재가': dp['optn_prpr'],
            '해당일 업종 시가': dp['optn_oprc'],
            '해당일 업종 고가': dp['optn_hgpr'],
            '해당일 업종 저가': dp['optn_lwpr'],
            '환율':exchange_rate,
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
    exchange_rate = get_exchange_rate(request)
    for dp in reversed(daily_price):
        chart_data = {
            '한국기준일자': dp['kymd'],
            '한국기준시간': dp['khms'],
            '종가': dp['last'],
            '시가': dp['open'],
            '고가': dp['high'],
            '저가': dp['low'],
            '환율':exchange_rate,
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
    image_path = os.path.join(settings.MEDIA_ROOT, f'{symbol}.jpg')
    if os.path.exists(image_path) or os.path.isfile(image_path):
        image_url = f'https://stalksound.store/image/{symbol}.jpg'
    else:
        image_url = 'https://stalksound.store/image/default.jpg'
    chart_data = {
        '거래량' : daily_price['tvol'],
        '전일종가': daily_price['base'],
        '$현재가': daily_price['last'],
        '현재가': int(float(daily_price['last'])*float(daily_price['t_rate'])),
        '고가': daily_price['high'],
        '저가': daily_price['low'],
        '시가': daily_price['open'],
        '시가총액': daily_price['tomv'],
        '등락율': daily_price['t_xrat'],
        '환율':daily_price['t_rate'],
        '전일 환율':daily_price['p_rate'],
        '이미지URL': image_url,     
    }
    stock = Stock.objects.get(symbol=symbol)
    user_stock = UserStock.objects.filter(stock=stock)

    if user_stock is not None:
        for user_stock in user_stock:
            if user_stock.having_quantity >= 1:
                now_stock_price=int(float(daily_price['last'])*float(daily_price['t_rate'])) * user_stock.having_quantity
                user_stock.profit_loss = user_stock.price - now_stock_price
                user_stock.now_price = now_stock_price
                user_stock.rate_profit_loss=(now_stock_price-user_stock.price)/user_stock.price*100
                user_stock.save()
    else:
        pass
    return JsonResponse({'chart_data': chart_data}, safe=False)