# blog_auto_project

IT 블로그 원고를 자동으로 쓰는 프로젝트에, 리서치 자료를 짧은 설명 영상(숏츠·릴스)으로 만드는 파이프라인을 붙이는 중이다.
진행 상황과 결정 사항은 `docs/HANDOFF.md`를 먼저 읽는다.

## 지금 있는 것 (블로그 원고)

- `main.py`: 카테고리 A(해외 IT 뉴스, `rss_parser.py`)와 B(IT 취업 키워드, `keywords_queue.txt`)를 번갈아 골라 원고를 쓰고 `post_Category_{A|B}.md`로 저장, 슬랙 알림.
- `content_generator.py`: 블로그 원고 프롬프트. Gemini 호출은 `gemini_client.py`를 쓴다.
- `keyword_extractor.py`: Serper로 키워드 큐 생성(수동 실행).
- `.github/workflows/blog_automation.yml`: 주기 실행 후 결과를 커밋.

## 숏츠 파이프라인 (진행 중)

- `gemini_client.py`: Gemini 공용 호출(재시도·대체 모델, `generate`, Pydantic 구조화 출력 `generate_json`). 블로그와 숏츠가 같이 쓴다.
- `shorts/pipeline/`: 2단계 대본 단계. `sources.py`(원문 읽기) → `stages.py`(분석·관점·스토리보드) → `verify.py`(원문 대조 검사) → `report.py`(검수용 `review.md`).
- `shorts/voice/`: 3단계 음성 단계. `typecast.py`(타임스탬프 포함 합성) → `voice.json`과 `audio/sceneN.wav`.
- `shorts/video/`: 4단계 영상 단계(Remotion). 실행 폴더를 public 폴더로 열어 `video.mp4`를 만든다. 장면 연출은 `src/scenes/`만 고친다.
- 결과물은 `.local/runs/`(git 제외)에 저장한다.

```bash
.venv/bin/pip install -r shorts/requirements.txt
.venv/bin/python -m shorts.pipeline --source paper.pdf
.venv/bin/python -m shorts.voice --run-dir .local/runs/<폴더>   # Typecast 크레딧 사용
cd shorts/video && npm install && npm run render -- --run-dir ../../.local/runs/<폴더>
.venv/bin/python -m pytest shorts
```

## 로컬 실행

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python main.py   # .env에 GEMINI_API_KEY 등 필요
```

`main.py`는 실행할 때마다 `post_Category_*.md`와 `category_state.txt`를 덮어쓴다. 로컬 테스트 뒤 이 변경은 커밋하지 않는다(`git checkout -- post_Category_*.md category_state.txt`).

## 작업 규칙

- **이 레포는 공개 레포다.** 회사 관점·브랜딩·구성원 제공 자료·내부 문서·API 키를 커밋하지 않는다. 로컬 전용 자료는 `.local/`(git 제외)에 둔다.
- **원문 기준으로 해석한다.** 영상·요약의 숫자와 주장은 원문과 대조한다. 상대적 의미를 절대적으로 바꾸거나(예: "A가 B보다 귀해진다" → "A의 가치가 커진다") 원문에 없는 결론을 만들지 않는다.
- **원문 내용과 우리 해석을 구분한다.** 해석 부분은 화면·문서에 "우리 해석"으로 표시한다.
- 이론 모델의 예시 숫자는 "예시값, 예측치 아님"을 밝힌다.
- 커밋·푸시는 사용자가 요청할 때만 한다. 작업은 브랜치에서 하고 PR로 올린다.
