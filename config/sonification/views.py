from io import BytesIO
import numpy as np
from scipy.io import wavfile
import mojito
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view

f = open("../../koreainvestment.key")
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
@api_view(['POST'])
def now_data(request):
    data = request.data
    symbol = data.get('symbol')
    resp = broker.fetch_price(symbol)
    chart_data = { 
        '전일대비부호': resp['output']['prdy_vrss_sign'],
        '전일 대비율': resp['output']['prdy_ctrt'],
        '시가': resp['output']['stck_oprc'],
        '현재가': resp['output']['stck_prpr'],
        '고가': resp['output']['stck_hgpr'],
        '저가': resp['output']['stck_lwpr']
    }
    return JsonResponse({'chart_data': chart_data}, safe=True)

#일봉(설정일 기준 30일 전까지 나옴)
@api_view(['POST'])
def il_bong(request):
    data = request.data 
    symbol = data.get('symbol')
    begin = data.get('begin')
    end = data.get('end')
    resp = broker.fetch_ohlcv(
        start_day=begin, #YYYYMMDD 형식 지킬 것
        end_day=end,
        symbol=symbol, #종목
        timeframe='D',  
        adj_price=True
    )
    daily_price = resp['output2']
    jm = resp['output1']['hts_kor_isnm'] #종목 ㅋㅋ
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
@api_view(['POST'])
def boon_bong(symbol,end):
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