import os
import requests
import json
import re
from dotenv import load_dotenv

load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def clean_title(title):
    """검색 결과 제목에서 불필요한 사이트명이나 특수기호를 제거합니다."""
    # ' - 사이트명' 또는 ' | 사이트명' 형태 잘라내기
    title = re.split(r'\s*[-|\||–]\s*', title)[0]
    # [채용공고], (주) 등 괄호 안의 내용 제거
    title = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    # 텍스트 양옆 공백 제거
    return title.strip()

def get_related_searches(query):
    """연관 검색어가 없으면 Organic 검색 결과의 제목을 추출합니다."""
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "gl": "kr",
        "hl": "ko",
        "tbs": "qdr:m"
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    
    results = []
    if response.status_code == 200:
        data = response.json()
        
        # 1. 최우선: 연관 검색어 (Related Searches)
        if 'relatedSearches' in data:
            results.extend([item['query'] for item in data['relatedSearches']])
            
        # 2. 차선: 많이 묻는 질문 (People Also Ask)
        if 'peopleAlsoAsk' in data:
            results.extend([item['question'] for item in data['peopleAlsoAsk']])
            
        # 3. ★ 신규 추가: 둘 다 없으면 Organic 결과의 '제목'을 키워드로 활용
        if not results and 'organic' in data:
            for item in data['organic']:
                cleaned = clean_title(item.get('title', ''))
                # 정제된 제목이 너무 짧지 않은 경우만 리스트에 추가 (최소 5글자 이상)
                if len(cleaned) > 5:
                    results.append(cleaned)
                    
        # 중복 제거 후 리스트로 반환
        return list(set(results))
    else:
        print(f"[오류] API 호출 실패: {response.status_code}")
        return []

def run_keyword_pipeline(seed_keyword, max_depth=3):
    print(f"🚀 키워드 추출 시작! 초기 시드: '{seed_keyword}'\n")
    
    collected_keywords = set()
    collected_keywords.add(seed_keyword)
    current_queue = [seed_keyword]

    for depth in range(1, max_depth + 1):
        print(f"--- [ {depth}세대 탐색 중... ] ---")
        next_queue = []
        
        for keyword in current_queue:
            related = get_related_searches(keyword)
            if not related:
                print(f"[{keyword}] ⚠️ 파생 데이터 없음")
                continue
                
            print(f"[{keyword}]의 파생 키워드: {related[:3]} ...")
            
            for r_word in related:
                if r_word not in collected_keywords:
                    collected_keywords.add(r_word)
                    next_queue.append(r_word)
        
        current_queue = next_queue
        
        if not current_queue:
            print("더 이상 파생되는 키워드가 없어 탐색을 종료합니다.")
            break

    return list(collected_keywords)

if __name__ == "__main__":
    # 시드 키워드 테스트
    SEED = "IT 취업" 
    
    final_keywords = run_keyword_pipeline(SEED, max_depth=2)
    
    with open("keywords_queue.txt", "w", encoding="utf-8") as f:
        for kw in final_keywords:
            f.write(kw + "\n")
            
    print(f"\n✅ 총 {len(final_keywords)}개의 키워드가 'keywords_queue.txt'에 저장되었습니다!")