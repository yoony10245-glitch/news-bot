import os
import requests
import urllib.parse
import telegram
import asyncio
import html  # [중요] 글자 깨짐 방지용 도구 추가
from datetime import datetime, timedelta, timezone
from newspaper import Article
from difflib import SequenceMatcher

# --- [설정 구역] ---
NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# 1. 키워드 설정
KEYWORDS = ["LIG넥스원", "LIG Nex1", "LIG D&A", "LIG 디펜스", "방산 수출"]

# 2. 검색 기간 (최근 60분)
TIME_LIMIT_MINUTES = 60 

# 3. 중복 기준 (70% 이상 같으면 차단)
SIMILARITY_THRESHOLD = 0.7

# --- [기능 구역] ---
def get_korea_time():
    """무조건 한국 시간(KST) 반환"""
    return datetime.now(timezone(timedelta(hours=9)))

def get_article_content(url):
    """기사 내용 긁어오기"""
    try:
        article = Article(url, language='ko')
        article.download()
        article.parse()
        
        title = article.title
        # 요약문이 없으면 본문 앞 100자 자르기
        if article.text:
            summary = article.text[:100] + "..."
        else:
            summary = "요약 내용을 가져올 수 없습니다."
            
        press = article.meta_site_name or "언론사 미상"
        return title, press, summary
    except:
        return None, None, None

def check_similarity(new_title, sent_titles):
    """중복 검사"""
    for sent in sent_titles:
        ratio = SequenceMatcher(None, new_title, sent).ratio()
        if ratio >= SIMILARITY_THRESHOLD:
            return True
    return False

async def main():
    print("🚀 [최종] 깔끔한 포맷 봇 시작 (한국시간 기준)")
    
    # 한국 시간 계산
    now = get_korea_time()
    time_limit = now - timedelta(minutes=TIME_LIMIT_MINUTES)
    sent_titles = [] 

    for keyword in KEYWORDS:
        print(f"🔍 검색: {keyword}")
        encText = urllib.parse.quote(keyword)
        
        # 최신순(date) 정렬
        url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display=10&sort=date"
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        
        try:
            res = requests.get(url, headers=headers)
            items = res.json().get('items', [])
            
            for item in items:
                # 1. 날짜 필터링 (한국시간 기준)
                pub_date_str = item['pubDate']
                pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                
                if pub_date > time_limit:
                    link = item['originallink'] if item['originallink'] else item['link']
                    
                    # 1차 제목 정리 (네이버 태그 제거)
                    temp_title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", "")
                    
                    if check_similarity(temp_title, sent_titles):
                        print(f"🚫 중복: {temp_title}")
                        continue
                    
                    # 2. 내용 긁어오기
                    real_title, press, summary = get_article_content(link)
                    
                    if not real_title:
                        real_title = temp_title
                        press = "네이버 뉴스"
                        summary = "본문 수집 실패 (링크 확인 필요)"

                    if check_similarity(real_title, sent_titles):
                        continue
                    
                    # --- [핵심: 요청하신 포맷 적용] ---
                    # html.escape: 특수문자(<, >)가 있어도 깨지지 않게 변환해줌
                    safe_title = html.escape(real_title)
                    safe_press = html.escape(press)
                    safe_summary = html.escape(summary)
                    
                    # [요청하신 순서] 제목 - 매체명 - 뉴스요약본 - 뉴스링크
                    msg = (
                        f"<b>[{safe_title}]</b>\n\n"
                        f"📰 <b>매체명:</b> {safe_press}\n"
                        f"📝 <b>요약:</b> {safe_summary}\n\n"
                        f"🔗 <a href='{link}'>기사 원문 보기</a>"
                    )
                    
                    bot = telegram.Bot(token=TELEGRAM_TOKEN)
                    # parse_mode='HTML'을 써야 굵은 글씨가 적용됨
                    await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML')
                    
                    print(f"✅ 전송: {real_title}")
                    sent_titles.append(real_title)

        except Exception as e:
            print(f"❌ 에러: {e}")

if __name__ == "__main__":
    asyncio.run(main())
