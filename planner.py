import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def select_best_topic_and_summarize():
    """keywords_queue.txt에서 최적의 주제를 선정하고 요약을 생성합니다."""
    
    # 1. 큐 파일 읽기
    if not os.path.exists("keywords_queue.txt"):
        return None
        
    with open("keywords_queue.txt", "r", encoding="utf-8") as f:
        keywords = f.readlines()
    
    if not keywords:
        return None

    # 2. Gemini에게 주제 선정 및 요약 요청
    # 모든 키워드를 다 던져주면 너무 많으므로 상위 20개 정도만 샘플링해서 전달합니다.
    keywords_str = "\n".join([k.strip() for k in keywords[:20]])
    
    prompt = f"""
    당신은 IT 전문 블로그 편집장입니다. 아래 리스트는 최근 수집된 IT 취업 관련 키워드들입니다.
    이 중에서 오늘 블로그에 포스팅했을 때 가장 유익하고 조회수가 잘 나올법한 '최적의 주제'를 하나만 선정해주세요.
    
    [키워드 리스트]
    {keywords_str}
    
    [출력 형식 (JSON 구조로 응답하세요)]
    {{
      "selected_keyword": "선정된 키워드",
      "title": "블로그에 쓸 매력적인 제목",
      "summary": "본문에서 다룰 핵심 내용 3가지 요약",
      "reason": "이 주제를 선정한 이유"
    }}
    """
    
    response = model.generate_content(prompt)
    
    # JSON 형태의 응답을 파싱 (Gemini가 마크다운 코드 블록으로 감쌀 수 있으므로 정제 필요)
    import json
    raw_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_text)