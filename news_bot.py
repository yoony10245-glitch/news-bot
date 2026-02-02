import os
import requests
import urllib.parse
import telegram
import asyncio

# --- [설정 불러오기] ---
NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

async def main():
    print("📢 [진단 모드] 봇 실행 시작!")
    
    # 1. 비밀번호 잘 가져왔나 확인 (앞 2글자만 보여줌)
    print(f"🔑 네이버 ID: {NAVER_CLIENT_ID[:2]}**" if NAVER_CLIENT_ID else "❌ 네이버 ID가 비어있음!")
    print(f"🔑 텔레그램 토큰: {TELEGRAM_TOKEN[:2]}**" if TELEGRAM_TOKEN else "❌ 토큰이 비어있음!")
    
    # 2. 강제로 '날씨' 검색해서 네이버 대답 듣기
    keyword = "날씨"
    url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(keyword)}&display=1"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}

    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        
        # [핵심] 네이버가 에러를 보냈는지 확인
        if 'errorMessage' in data:
            print(f"❌ [치명적 오류] 네이버가 거절함: {data['errorMessage']}")
            print("👉 해결책: Secrets에서 네이버 아이디/비번을 다시 확인하세요. (띄어쓰기 주의)")
            return

        items = data.get('items', [])
        if not items:
            print("❓ 이상하다.. 날씨 뉴스가 0개일 리가 없는데?")
            return

        print(f"✅ 네이버 연결 성공! (첫번째 제목: {items[0]['title']})")
        
        # 3. 텔레그램 강제 전송
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=f"🔔 테스트 성공! 네이버 연결됨.\n뉴스: {items[0]['title']}")
        print("🚀 텔레그램 전송까지 완료!")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(main())
