import os
import time
import requests # 슬랙 웹훅용
from rss_parser import fetch_latest_it_news
from content_generator import select_best_topic_and_summarize, generate_mentoring_post, generate_news_post

STATE_FILE = "category_state.txt"

def get_next_category():
    """이전 실행 기록을 읽어 이번에 실행할 카테고리를 결정합니다."""
    if not os.path.exists(STATE_FILE):
        return "A" # 처음 실행할 때는 A부터 시작
        
    with open(STATE_FILE, "r") as f:
        last_category = f.read().strip()
        
    # A였으면 B로, B였으면 A로 전환
    return "B" if last_category == "A" else "A"

def save_current_category(category):
    """현재 실행한 카테고리를 저장합니다."""
    with open(STATE_FILE, "w") as f:
        f.write(category)

def run_automation():
    print("--- 🤖 IT 블로그 자동화 시스템 가동 ---")
    current_category = get_next_category()
    print(f"🔄 이번 턴은 [카테고리 {current_category}] 입니다.\n")

    if current_category == "A":
        # === 카테고리 A: 최신 IT 뉴스 ===
        news_list = fetch_latest_it_news()
        if not news_list:
            print("❌ 뉴스를 가져오지 못했습니다.")
            return
            
        # 가장 첫 번째(최신) 기사를 선택
        target_news = news_list[0]
        title_for_image = target_news['title']
        
        # 원고 작성
        draft = generate_news_post(target_news)

    else:
        # === 카테고리 B: 취업 멘토링 정보 ===
        plan = select_best_topic_and_summarize()
        if not plan:
            print("❌ 키워드 큐가 비어있습니다. keyword_extractor.py를 먼저 실행하세요.")
            return
            
        print(f"📌 선정된 주제: {plan['title']}")
        title_for_image = plan['title']
        
        time.sleep(5) # API 할당량 보호 (429 에러 방지)
        
        # 원고 작성
        draft = generate_mentoring_post(plan)

    filename = f"post_Category_{current_category}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(draft)
    print(f"✅ 원고 작성 완료 ({filename})")

    time.sleep(5) # API 할당량 보호
    
    # 모든 작업 완료 후 상태 저장
    save_current_category(current_category)
    print(f"\n다음 실행 시에는 카테고리 {'B' if current_category == 'A' else 'A'}가 실행됩니다.")
    
    # 슬랙 알림 쏘기!
    send_slack_notification(current_category, title_for_image, filename)
    print("\n🎉 모든 작업 완료!")
    
def send_slack_notification(category, title, filename):
    """슬랙으로 완료 알림을 전송합니다."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("⚠️ 슬랙 웹훅 URL이 설정되지 않아 알림을 생략합니다.")
        return

    message = {
        "text": f"🎉 *새로운 블로그 원고 자동 생성 완료!*\n\n* 카테고리: {category}\n* 제목: {title}\n* 파일명: {filename}\n\nGitHub 저장소에서 원고를 확인해 주세요! 🚀"
    }
    try:
        requests.post(webhook_url, json=message)
        print("🔔 슬랙 알림 전송 완료!")
    except Exception as e:
        print(f"❌ 슬랙 알림 전송 실패: {e}")


if __name__ == "__main__":
    run_automation()