import os
from google.genai import Client # 새로운 패키지 호출 방식
from dotenv import load_dotenv
import json

load_dotenv()
client = Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.5-flash"

def select_best_topic_and_summarize():
    """[카테고리 B] keywords_queue.txt에서 최적의 주제 선정"""
    if not os.path.exists("keywords_queue.txt"):
        return None
    with open("keywords_queue.txt", "r", encoding="utf-8") as f:
        keywords = f.readlines()
    if not keywords:
        return None

    keywords_str = "\n".join([k.strip() for k in keywords[:20]])
    prompt = f"""
    당신은 IT 전문 블로그 편집장입니다. 다음 키워드 중 하나를 선정해 기획안을 작성하세요.
    [키워드 리스트]: {keywords_str}
    [출력 형식 (반드시 순수 JSON 구조로만 응답)]:
    {{"selected_keyword": "키워드", "title": "제목", "summary": "핵심 3가지 요약", "reason": "이유"}}
    """
    
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    try:
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"❌ JSON 파싱 에러: {e}")
        return None

def generate_mentoring_post(topic_data):
    """[카테고리 B] 취업 멘토링 원고 작성"""
    print("✍️ [카테고리 B] 취업 멘토링 원고 작성 중...")
    prompt = f"""
    당신은 IT 취업 전문 멘토 "성장하는IT" 입니다. 아래 기획안을 바탕으로 네이버 블로그 마크다운 원고를 작성하세요.
    - 주제: {topic_data['selected_keyword']}
    - 제목: {topic_data['title']}
    - 요약: {topic_data['summary']}

    [작성 가이드]
    1. 톤앤매너: 이모티콘 사용을 엄격히 자제하세요. 취준생의 고민에 깊이 공감하는 '진중하고 친절한' 선배의 어조를 유지하세요.
    2. 전문성: 추상적인 응원보다는 실무와 채용 시장에 기반한 현실적이고 구체적인 조언을 제공하세요.
    3. 가독성: 소제목(##)으로 흐름을 나누고, 문단은 짧게 끊어주세요.
    4. 마무리: 독자가 자신의 상황을 돌아볼 수 있는 차분한 질문을 던지며 마무리하고, 관련 해시태그 5개를 추가하세요.
    """
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    return response.text

def generate_news_post(news_data):
    """[카테고리 A] 해외 IT 뉴스 원고 작성"""
    print("✍️ [카테고리 A] 해외 IT 뉴스 원고 작성 중...")
    prompt = f"""
    당신은 IT 테크 전문 블로거 "성장하는IT" 입니다. 아래 해외 기사 요약을 바탕으로 네이버 블로그 마크다운 원고를 작성하세요.
    - 기사 제목: {news_data['title']}
    - 기사 내용: {news_data['summary']}
    - 출처: {news_data['source']}

    [작성 가이드]
    1. 톤앤매너: 이모티콘 사용을 엄격히 자제하세요. 신뢰감을 주는 객관적이고 '진중한 전문가'의 어조를 유지하세요.
    2. 인사이트: 단순 번역을 넘어, 이 기술/이슈가 한국 IT 실무자들에게 어떤 영향을 미칠지 분석을 한 스푼 더해주세요.
    3. 가독성: 소제목(##)과 글머리 기호(-)를 활용해 정보를 깔끔하게 정리하세요.
    4. 마무리: 독자의 의견을 묻는 정중한 질문과 함께 해시태그 5개를 추가하세요.
    """
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    return response.text