import os
import requests
import urllib.parse
from bs4 import BeautifulSoup
import telegram
import asyncio
from datetime import datetime, timedelta
from newspaper import Article
from difflib import SequenceMatcher

# --- [설정] ---
# 1. 깃허브 비밀번호 가져오기
NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID') # Secrets에 CHAT_ID도 추가해두셨죠?

# 2. 키워드 (뉴스 등 불필요한 단어 제거)
KEYWORDS = ["LIG넥스원", "LIGNex1", "LIGD&A", "날씨"]

# 3. 중복 차단 기준 (70% 이상 같으면 중복)
SIMILARITY_THRESHOLD = 0.7 

# --- [기능] ---
def get_article_content(url):
    """외부 기사 내용 긁어오기 (newspaper3k 사용)"""
    try:
        article = Article(url, language='ko')
        article.download()
        article.parse()
        title = article.title
        # 본문 100자 요약
        summary = article.text[:100] + "..." if article.text else "요약 없음"
        press = article.meta_site_name or "언론사 미상"
        return title, press, summary
    except:
        return None, None, None

async def send_alert(title, press, summary, link):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    msg = f"🚨 <b>{title}</b>\n📰 <b>{press}</b>\n📝 {summary}\n🔗 {link}"
    try:
        if CHAT_ID:
            await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')
            print(f"전송 성공: {title}")
    except Exception as e:
        print(f"전송 실패: {e}")

def check_similarity(new_title, sent_titles):
    """방금 보낸 기사들과 제목이 비슷한지 검사"""
    for sent in sent_titles:
        ratio = SequenceMatcher(None, new_title, sent).ratio()
        if ratio >= SIMILARITY_THRESHOLD:
            return True # 중복임
    return False

async def main():
    print("🚀 깃허브 프로 봇 실행!")
    
    # 깃허브는 15~20분마다 돌므로, 최근 20분 기사만 가져옴
    time_limit = datetime.now() - timedelta(minutes=20)
    sent_titles = [] # 이번 실행에서 보낸 기사 제목들 저장 (중복 방지용)

    for keyword in KEYWORDS:
        print(f"🔍 검색: {keyword}")
        encText = urllib.parse.quote(keyword)
        url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display=10&sort=date"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        
        try:
            res = requests.get(url, headers=headers)
            items = res.json().get('items', [])
            
            for item in items:
                # 날짜 확인 (최근 20분 것만)
                pub_date_str = item['pubDate']
                pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z").replace(tzinfo=None)
                
                if pub_date > time_limit:
                    # 아웃링크(originallink) 우선 사용
                    final_link = item['originallink'] if item['originallink'] else item['link']
                    
                    # 1차 제목 (네이버 제공)
                    temp_title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", "")
                    
                    # 중복 검사 (이번 실행에서 이미 보낸 것과 비교)
                    if check_similarity(temp_title, sent_titles):
                        print(f"🚫 중복 차단: {temp_title}")
                        continue

                    # 내용 긁어오기
                    real_title, press, summary = get_article_content(final_link)
                    
                    if real_title:
                        # 진짜 제목으로 한번 더 중복 체크
                        if check_similarity(real_title, sent_titles):
                            continue
                            
                        await send_alert(real_title, press, summary, final_link)
                        sent_titles.append(real_title) # 보낸 목록에 추가

        except Exception as e:
            print(f"에러: {e}")

if __name__ == "__main__":
    asyncio.run(main())

