import feedparser

def fetch_latest_it_news():
    """해외 주요 IT 매체의 RSS 피드를 읽어 최신 기사를 추출합니다."""
    
    # 타겟 RSS 피드 주소 (언제든 추가/변경 가능)
    rss_urls = {
        "TechCrunch (AI)": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "The Verge (Tech)": "https://www.theverge.com/tech/rss/index.xml"
    }
    
    collected_news = []

    for source_name, url in rss_urls.items():
        print(f"📡 [{source_name}] 피드 읽는 중...")
        feed = feedparser.parse(url)
        
        # 피드 연결에 실패했거나 글이 없는 경우 방어 로직
        if feed.bozo or not feed.entries:
            print(f"⚠️ [{source_name}] 피드를 불러오는 데 실패했습니다.")
            continue
            
        # 각 매체별로 가장 최신 기사 2개씩만 가져오기
        for entry in feed.entries[:2]:
            title = entry.title
            link = entry.link
            
            # 본문 요약 (HTML 태그가 섞여 있을 수 있으나, 나중에 Gemini가 알아서 정제해 줍니다)
            # 매체마다 summary 또는 description 태그를 사용하므로 안전하게 가져옵니다.
            summary = entry.get('summary', entry.get('description', '내용 없음'))
            
            collected_news.append({
                "source": source_name,
                "title": title,
                "link": link,
                "summary": summary
            })
            print(f"  -> 수집 완료: {title}")

    return collected_news

if __name__ == "__main__":
    print("🚀 해외 IT 최신 뉴스 수집 시작!\n")
    
    latest_news = fetch_latest_it_news()
    
    print("\n✅ 수집된 기사 목록:")
    print("-" * 50)
    for i, news in enumerate(latest_news, 1):
        print(f"{i}. [{news['source']}] {news['title']}")
        print(f"   링크: {news['link']}")
        print("-" * 50)
        
    # 나중에 이 리스트 중 하나를 선택해서 Gemini에게 번역 및 블로그 작성을 지시하게 됩니다.