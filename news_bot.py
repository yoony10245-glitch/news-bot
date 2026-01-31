import requests
import urllib.parse
from bs4 import BeautifulSoup
import telegram
import asyncio
import os
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# --- [설정] ---
NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# ▼▼▼ [여기서 키워드를 수정하시면 됩니다!] ▼▼▼
KEYWORDS = ["LIGD&A", "LIG넥스원", "날씨"] 

# --- [시간 계산 함수] ---
def is_recent_news(pubDate_str):
    try:
        news_time = parsedate_to_datetime(pubDate_str)
        now = datetime.now(news_time.tzinfo)
        if (now - news_time) < timedelta(minutes=7):
            return True
        return False
    except:
        return False

# --- [뉴스 검색 및 전송] ---
def get_news(keyword):
    encText = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display=10&sort=date"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    try:
        res = requests.get(url, headers=headers)
        return res.json().get('items', []) if res.status_code == 200 else []
    except: return []

def get_details(link):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(link, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        press = soup.find('meta', property='og:site_name')
        summary = soup.find('meta', property='og:description')
        return (press['content'] if press else "미상"), (summary['content'] if summary else "")
    except: return "확인불가", ""

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ 오류: Secrets 설정이 안 됐습니다.")
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    print("🔍 뉴스 탐색 시작...")

    sent_count = 0

    for keyword in KEYWORDS:
        items = get_news(keyword)
        for item in items:
            link = item['link']
            pubDate = item['pubDate']

            if "naver.com" not in link: continue
            if not is_recent_news(pubDate): continue

            title = BeautifulSoup(item['title'], 'html.parser').get_text()
            press, summary = get_details(link)
            mobile_link = link.replace("https://news.naver.com", "https://m.news.naver.com")
            msg = f"🚨 <b>{title}</b>\n\n📰 <b>{press}</b>\n📝 {summary}\n\n🔗 <a href='{mobile_link}'>기사 보기</a>"

            try:
                await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')
                sent_count += 1
                await asyncio.sleep(1)
            except Exception as e:
                print(f"전송 실패: {e}")

    print(f"🏁 탐색 종료. ({sent_count}건 전송)")

if __name__ == "__main__":
    asyncio.run(main())
