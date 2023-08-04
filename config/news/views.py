from django.shortcuts import render
from django.http import JsonResponse  
from bs4 import BeautifulSoup
import requests,codecs, re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager



def get_specific_news(request): # 뉴스 아이디를 통해 특정 뉴스의 글을 반환
    article_id = request.GET.get('article_id')
    office_id = request.GET.get('office_id')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.implicitly_wait(1)
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
    return JsonResponse(news_obj,json_dumps_params={'ensure_ascii': False})

def get_news_by_stock_code(request): # 특정 종목의 뉴스리스트를 반환
    stock_code = request.GET.get('stock_code')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.implicitly_wait(3)
    driver.get('https://finance.naver.com/item/news.naver?code='+ stock_code)
    html = driver.page_source
    soup = BeautifulSoup(html,'html.parser')

    news_list = {}
    for i in range(1,10):
        news_a_tag = soup.select('body > div > table.type5 > tbody > tr:nth-child('+ str(1 + i) +') > td.title > a')
        article_id = news_a_tag[0].get('href').split('article_id=')[1].split('&')[0]
        office_id = news_a_tag[0].get('href').split('office_id=')[1].split('&')[0]
        news_provider = soup.select('body > div > table.type5 > tbody > tr.tr:nth-child('+ str(1 + i) +') > td.info')[0].text
        news_created_at = soup.select('body > div > table.type5 > tbody > tr:nth-child('+ str(1 + i) +') > td.date')[0].text
        created_at_datetime = datetime.strptime(news_created_at, '%Y-%m-%d %H:%M')
        time_difference = datetime.now() - created_at_datetime
        minite_difference = time_difference.days * 24 * 60 + time_difference.seconds // 60
        news_title = news_a_tag[0].text
        news_obj = {
            "news_title":news_title,
            "article_id":article_id,
            "office_id":office_id,
            "news_provider":news_provider,
            "created_at":news_created_at,
            "time_difference":minite_difference,
        }
        news_list[i] = news_obj
    return JsonResponse(news_list,json_dumps_params={'ensure_ascii': False})

def get_realtime_news(self): # 실시간 모든 종목의 뉴스리스트 10개를 반환
    news_url = 'https://finance.naver.com/news/news_list.naver'
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"}
    res = requests.get(news_url,headers=headers)
    soup = BeautifulSoup(res.text,'html.parser')
    news_list = {}
    for i in range(10):
        news_a_tag = soup.select('#contentarea_left > ul > li.newsList.top > dl > dt:nth-child('+ str(1 + 3 * i) + ') > a')
        article_id = news_a_tag[0].get('href').split('article_id=')[1].split('&')[0]
        office_id = news_a_tag[0].get('href').split('office_id=')[1].split('&')[0]
        news_img_tag = soup.select('#contentarea_left > ul > li.newsList.top > dl > dt:nth-child('+ str(1 + 3 * i) + ') > a > img')
        news_provider = soup.select('#contentarea_left > ul > li.newsList.top > dl > dd:nth-child('+ str(3 + 3 * i) + ') > span.press')[0].text


        news_created_at = soup.select('#contentarea_left > ul > li.newsList.top > dl > dd:nth-child('+ str(3 + 3 * i) + ') > span.wdate')[0].text
        created_at_datetime = datetime.strptime(news_created_at, '%Y-%m-%d %H:%M')
        time_difference = datetime.now() - created_at_datetime
        minite_difference = time_difference.days * 24 * 60 + time_difference.seconds // 60
        try:
            news_img_src = news_img_tag[0].get('src')
        except(AttributeError):
            news_img_src = ""
        news_title_tag = soup.select('#contentarea_left > ul > li.newsList.top > dl > dd:nth-child('+ str(2 + 3 * i) + ') > a')
        news_title = news_title_tag[0].get('title')
        news_obj = {
            "news_img_src":news_img_src,
            "news_title":news_title,
            "article_id":article_id,
            "office_id":office_id,
            "news_provider":news_provider,
            "created_at":news_created_at,
            "time_difference":minite_difference,
        }
        news_list[i] = news_obj
    return JsonResponse(news_list,json_dumps_params={'ensure_ascii': False})
