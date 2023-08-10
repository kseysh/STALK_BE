from django.http import JsonResponse  
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timezone

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService

from webdriver_manager.chrome import ChromeDriverManager
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions 
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view,permission_classes,authentication_classes

@swagger_auto_schema(
    method='get',
    operation_id='특정 뉴스 조회',
    operation_description='article_id, office_id를 통해 특정 뉴스 조회, 로딩 시간 좀 걸림',
    tags=['뉴스 조회'],
    manual_parameters=[
        openapi.Parameter('article_id', in_=openapi.IN_QUERY, description='article_id ex) 0005296289', type=openapi.TYPE_STRING),
        openapi.Parameter('office_id', in_=openapi.IN_QUERY, description='office_id ex) 277', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def get_specific_news(request): # 뉴스 아이디를 통해 특정 뉴스의 글을 반환
    article_id = request.GET.get('article_id')
    office_id = request.GET.get('office_id')
    # chrome_service = Service('/usr/bin/chromedriver')
    
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=ChromeService('/usr/bin/chromedriver'),options=chrome_options)
    
    driver.get('https://finance.naver.com/news/news_read.naver?article_id='+ article_id +'&office_id='+ office_id)
    
    html = driver.page_source
    soup = BeautifulSoup(html,'html.parser')

    news_title = soup.select('#contentarea_left > div.boardView.size4 > div.article_header > div.article_info > h3')[0].text.strip()
    news_content = soup.select('#content')[0].text.strip()
    reporter_name = soup.select('#contentarea_left > div.boardView.size4 > div.card_journalist > div.info_thumb > a > span')[0].text
    reporter_image =  soup.select('#contentarea_left > div.boardView.size4 > div.card_journalist > a > img')[0].get('src')
    created_at = soup.select('#contentarea_left > div.boardView.size4 > div.article_header > div.article_info > div > span')[0].text

    news_obj = {
            "news_title":news_title,
            "news_content":news_content,
            "reporter_name":reporter_name,
            "reporter_image":reporter_image,
            "created_at":created_at,
        }
    driver.quit()
    return JsonResponse(news_obj,json_dumps_params={'ensure_ascii': False})

@swagger_auto_schema(
    method='get',
    operation_id='특정 종목 뉴스 리스트 조회',
    operation_description='stock_code를 통해 뉴스 리스트 조회',
    tags=['뉴스 조회'],
    manual_parameters=[
        openapi.Parameter('stock_code', in_=openapi.IN_QUERY, description='stock_code ex) 005930', type=openapi.TYPE_STRING),
    ],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def get_news_by_stock_code(request): # 특정 종목의 뉴스리스트를 반환
    stock_code = request.GET.get('stock_code')
    search_url = 'https://openapi.naver.com/v1/search/news.json?query='+ stock_code +'&display=100&start=1&sort=date'
    headers = {
            'X-Naver-Client-Id': 'UH6uGY8jqImX8dvrJvux',
            'X-Naver-Client-Secret': 'VoBSlnANAJ',
        }
    naver_request = requests.get(search_url,headers=headers)
    req_json = naver_request.json()
    filtered_items = {}
    count = 0
    for item in req_json["items"]:
        link = item["link"]
        if link.startswith("https://n.news.naver.com/mnews/"):
            title = item["title"]
            pubDate_str = item["pubDate"]
            pubDate = datetime.strptime(pubDate_str, '%a, %d %b %Y %H:%M:%S %z')
            current_time = datetime.now(timezone.utc)
            time_difference = (current_time - pubDate).total_seconds() // 60
            if time_difference>1440:
                time_difference= time_difference//1440
                time_difference = str(int(time_difference)) + '일 전'
            elif time_difference>60:
                time_difference = time_difference//60
                time_difference = str(int(time_difference)) + '시간 전'
            else :
                time_difference = str(int(time_difference)) + '분 전'
                
            article_id = link.split("/article/")[1].split("?sid=")[0].split("/")[-1]
            office_id = link.split("/mnews/article/")[1].split("/")[0]
            count += 1
            filtered_items[count] = {
                "title": title,
                "created_at": pubDate_str,
                "article_id": article_id,
                "office_id":office_id,
                "time_difference":time_difference
            }

    return JsonResponse(filtered_items, json_dumps_params={'ensure_ascii': False})

@swagger_auto_schema(
    method='get',
    operation_id='많이 본 뉴스 리스트 조회',
    operation_description='10개의 뉴스 리스트를 조회',
    tags=['뉴스 조회'],
)
@api_view(['GET'])
@authentication_classes([SessionAuthentication,BasicAuthentication])
@permission_classes([permissions.AllowAny])
def get_realtime_news(self): # 많이 본 뉴스리스트 10개를 반환
    # news_url = 'https://finance.naver.com/news/news_list.naver' # 모든 뉴스 리스
    news_url = 'https://finance.naver.com/news/news_list.naver?mode=RANK'
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"}
    res = requests.get(news_url,headers=headers)
    soup = BeautifulSoup(res.text,'html.parser')
    news_list = {}
    count = 0
    for j in range(1,3):
        for i in range(1,6):
            news_a_tag = soup.select('#contentarea_left > div.hotNewsList > ul > li:nth-child('+ str(j) +') > ul > li:nth-child('+ str(i) +') > a')
            news_title = news_a_tag[0].text
            article_id = news_a_tag[0].get('href').split('article_id=')[1].split('&')[0]
            office_id = news_a_tag[0].get('href').split('office_id=')[1].split('&')[0]
            news_provider = soup.select('#contentarea_left > div.hotNewsList > ul > li:nth-child('+ str(j) +') > ul > li:nth-child('+ str(i) +') > span.press')[0].text
            news_created_at = soup.select('#contentarea_left > div.hotNewsList > ul > li:nth-child('+ str(j) +') > ul > li:nth-child('+ str(i) +') > span.wdate')[0].text
            created_at_datetime = datetime.strptime(news_created_at, '%Y-%m-%d %H:%M')
            time_difference = datetime.now() - created_at_datetime
            minite_difference = time_difference.days * 24 * 60 + time_difference.seconds // 60
            if minite_difference>1440:
                minite_difference= minite_difference//1440
                minite_difference = str(minite_difference) + '일 전'
            elif minite_difference>60:
                minite_difference = minite_difference//60
                minite_difference = str(minite_difference) + '시간 전'
            else :
                minite_difference = str(minite_difference) + '분 전'
            news_obj = {
                "news_title":news_title,
                "article_id":article_id,
                "office_id":office_id,
                "news_provider":news_provider,
                "created_at":news_created_at,
                "time_difference":minite_difference,
            }
            count += 1
            news_list[count] = news_obj

    
    return JsonResponse(news_list,json_dumps_params={'ensure_ascii': False})