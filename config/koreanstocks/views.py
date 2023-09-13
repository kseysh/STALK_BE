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

payload = []

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

####국내주식 시가총액 기준####
@swagger_auto_schema(
    method='get',
    operation_id='시가총액기준 정렬(100개)',
    operation_description= '시가총액기준 정렬(100개)',
    tags=['주식 데이터']
)
@api_view(['GET'])
def transaction_rank(request):
    headers = {
        'content-type': 'application/json; charset=utf-8',
        'authorization' : broker.access_token,
        'appkey': key,
        'appsecret': secret,
        'tr_id': 'HHKST03900400',
        'custtype':'P',
    }
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/psearch-result?user_id=@2108665&seq=0"
    response = requests.get(url, headers=headers)
    response_data = response.json() 
    transaction_data_list = []
    for item in response_data['output2']:
        image_path = os.path.join(settings.MEDIA_ROOT, f'{item["code"]}.jpg')
        if os.path.isfile(image_path):
            image_url = f'https://stalksound.store/image/{item["code"]}.jpg'
        else:
            image_url = 'https://stalksound.store/image/default.jpg'
        data = {
            '종목명': item['name'],
            '종목코드': item['code'],
            '시가총액' : float(item['stotprice']),
            '현재가':float(item['price']),
            '전일 대비율': float(item['chgrate']),
            '대비': float(item['change']),
            '이미지URL': image_url,
        }
        try:
            stock = Stock.objects.get(
            symbol=item['code'],
            name=item['name'],
            )
            like=stock.likes
            data['좋아요 개수'] = like
            transaction_data_list.append(data)
        except ObjectDoesNotExist:
            try:
                stock = Stock.objects.create(
                symbol=item['code'],
                name=item['name'],
                is_domestic_stock = False,
                stock_image=f'{item["code"]}.jpg'
                )
                data['좋아요 개수'] = 0
                transaction_data_list.append(data)
            except:
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
def now_data(request):
    symbol = request.GET.get('symbol')
    resp = broker.fetch_price(symbol)
    image_path = os.path.join(settings.MEDIA_ROOT, f'{symbol}.jpg')
    if os.path.exists(image_path) or os.path.isfile(image_path):
        image_url = f'https://stalksound.store/image/{symbol}.jpg'
    else:
        image_url = 'https://stalksound.store/image/default.jpg'

    chart_data = { 
        '전일대비부호': resp['output']['prdy_vrss_sign'],
        '전일 대비율': resp['output']['prdy_ctrt'],
        '누적 거래량': resp['output']['acml_vol'],
        'HTS 시가총액': resp['output']['hts_avls'],
        '시가': resp['output']['stck_oprc'],
        '현재가': resp['output']['stck_prpr'],
        '고가': resp['output']['stck_hgpr'],
        '저가': resp['output']['stck_lwpr'],
        '이미지URL': image_url
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
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice?FID_COND_MRKT_DIV_CODE=U&fid_input_iscd={}&fid_input_date_1={}&fid_input_date_2={}&fid_period_div_code=D".format(symbol, start, end)

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
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice?FID_COND_MRKT_DIV_CODE=U&FID_INPUT_ISCD={}&FID_INPUT_DATE_1={}&FID_INPUT_DATE_2={}&FID_PERIOD_DIV_CODE=W".format(symbol, start, end)

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
def hmm__minute_data(request):
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
