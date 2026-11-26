"""대본 단계의 세 단계: 분석 → 관점 해석 → 스토리보드. 각 단계는 Gemini 구조화 출력을 쓴다."""
from pathlib import Path

import gemini_client

from . import timing
from .schemas import Analysis, Perspective, SourceDoc, Storyboard

# 관점 가이드는 공개 레포에 올리지 않는다. 없으면 중립 해설로 동작한다.
DEFAULT_PERSPECTIVE_PATH = Path(".local/perspective.md")
NEUTRAL_PERSPECTIVE = (
    "특정 회사·브랜드 관점 없이, 한국의 IT 실무자와 취업 준비생이 이 내용을 "
    "자기 일과 진로에 어떻게 연결해 볼 수 있을지 차분하게 풀어 준다."
)

ACCURACY_RULES = """
[정확성 규칙: 반드시 지킨다]
- 원문에 없는 결론을 만들지 않는다.
- 상대 비교를 절대적 주장으로 바꾸지 않는다. 예: 원문이 "A가 B보다 상대적으로 더 받는다"인데 "A의 가치가 커진다"로 쓰면 틀린다(A의 절대값은 떨어졌을 수 있다).
- 숫자는 원문 표기를 그대로 쓰고, 어떤 조건·설정에서 나온 숫자인지 기억한다. 설정이 다른 숫자를 한 비교에 섞지 않는다.
- 이론 모델의 예시값은 예측치가 아니다. 예시값임을 분명히 한다.
- 원문이 어떤 집단이 "사라진다"고 하지 않았다면 그렇게 그리지 않는다(예: 틈새로 이동하는 것과 실업은 다르다).
- 원문의 가능성·정도 표현을 지운 채 단정하지 않는다. could·may·potentially → "~할 수 있다", "~일 가능성", weakly → "약하게", about·around → "약". 예: "could be affected"를 "영향받습니다"로 쓰면 틀린다.
- 상관관계를 수준이나 인과로 바꾸지 않는다. 예: "글쓰기 능력은 노출도와 양의 상관"을 "글쓰기는 노출도가 높다"나 "글쓰기 때문에 노출된다"로 쓰면 틀린다.
- 원문에 없는 비교 대상을 만들지 않는다(예: 원문에 없는 "A 자체보다"를 덧붙이지 않는다).
""".strip()


def analyze(source: SourceDoc) -> Analysis:
    system = f"""당신은 리서치 자료를 정확하게 읽는 분석가입니다.
원문을 읽고 핵심 주장과 숫자를 뽑습니다. 출력의 설명은 한국어로 쓰되,
quote 필드는 원문 언어 그대로, 원문에서 한 글자도 바꾸지 않고 복사합니다(번역·요약 금지, 1~2문장 길이).

{ACCURACY_RULES}"""
    prompt = f"""다음 원문을 분석하세요.
- claims: 60초 영상에 쓸 만한 핵심 주장 5~10개.
- numbers: 영상에 나올 수 있는 중요한 숫자. value는 원문 표기 그대로.
  한 문장에 기준값·조건값이 함께 있으면(예: "80% of workers ... at least 10% of tasks"의 10%) 그것도 따로 적는다.
- caveats: 원문이 밝힌 한계, 영상에서 오해하기 쉬운 지점.
  특히 핵심 지표가 무엇을 뜻하지 않는지(예: "노출"은 일자리 대체인지 보완인지 구분하지 않는다)를 빠뜨리지 않는다.
  한계도 원문 표현의 강도 그대로 옮긴다("구분하지 않는다"를 "대체가 아니다"로 바꾸지 않는다).

[원문 제목] {source.title}
[원문]
{source.text}"""
    return gemini_client.generate_json(prompt, Analysis, system=system)


def load_perspective_guide(path: Path | None = None) -> tuple[str, str]:
    """(가이드 본문, 출처 설명)을 돌려준다."""
    path = path or DEFAULT_PERSPECTIVE_PATH
    if path.exists():
        return path.read_text(encoding="utf-8"), str(path)
    return NEUTRAL_PERSPECTIVE, "중립 해설(관점 가이드 없음)"


def interpret(analysis: Analysis, guide: str) -> Perspective:
    system = f"""당신은 리서치 내용을 정해진 관점으로 풀어 주는 해설자입니다.
해석은 원문 내용이 아니라 '우리 해석'입니다. 원문이 말한 것처럼 쓰지 않습니다.
모든 해석은 analysis의 claim에 근거해야 하고, based_on에 그 claim id를 적습니다.

{ACCURACY_RULES}

[관점 가이드]
{guide}"""
    prompt = f"""아래 분석 결과를 관점 가이드에 따라 해석하세요. 해석은 2~4개.

[분석 결과]
{analysis.model_dump_json(indent=2)}"""
    return gemini_client.generate_json(prompt, Perspective, system=system)


def write_storyboard(analysis: Analysis, perspective: Perspective) -> Storyboard:
    min_s, max_s = timing.TARGET_SECONDS
    system = f"""당신은 세로형 숏츠(1080×1920) 해설 영상의 스토리보드 작가입니다.

[형식]
- 전체 {min_s}~{max_s}초, 장면 {timing.MIN_SCENES}~{timing.MAX_SCENES}개.
- 내레이션 전체는 공백을 빼고 약 {timing.target_chars_low()}~{timing.target_chars_high()}자.
- 첫 장면(hook)은 3초 안에 궁금증을 만든다. 마지막 장면은 closing.
- on_screen_text는 장면당 1~3줄, 줄마다 짧게.

[내레이션 표기: TTS가 그대로 읽는다]
- 아라비아 숫자와 영문을 쓰지 않고 읽는 소리대로 한글로 적는다.
  예: 10배 → 열 배, 1인당 → 일인당, 2.41 → 이 점 사일, 40% → 사십 퍼센트, AGI → 에이지아이, Agent → 에이전트.
- 화면 문구(on_screen_text)에는 숫자를 그대로 써도 된다.

[근거 표시]
- 화면에 나오는 숫자는 모두 numbers에 적는다. 원문 숫자면 source_number_id에 analysis의 id를 적는다.
- 예시값을 화면에 쓰면 is_illustrative를 true로 하고, on_screen_text에 "예시값, 예측치 아님"을 넣는다.
- 우리 해석을 쓰는 장면은 purpose를 "interpretation"으로 하고, interpretation_ids를 채우고,
  on_screen_text 첫 줄을 "우리 해석"으로 한다. 원문 내용 장면에는 해석을 섞지 않는다.
- 원문 내용 장면은 claim_ids에 근거 claim id를 적는다.
- 화면 숫자는 analysis.numbers에 있는 값만 쓴다. 거기 없는 숫자는 화면에 쓰지 않는다(예시값 제외).
- 숫자를 쓸 때 그 숫자의 조건을 같은 장면에 함께 쓴다. hook도 마찬가지다.
  예: "80% of workers could have at least 10% of tasks affected"를 "80%가 영향받는다"로만 쓰면 틀린다(최소 10% 업무라는 조건이 빠졌다).

[원문 한계]
- analysis.caveats 가운데 영상의 핵심 메시지를 오해하게 만들 수 있는 것을 하나 이상 원문 내용 장면의 내레이션이나 화면에 넣는다.
- 한계를 옮길 때 원문 표현보다 세게 쓰지 않는다. 예: "대체인지 보완인지 구분하지 않는다"를 "대체를 의미하지 않는다"로 쓰면 틀린다.
- hook과 closing도 caveats와 어긋나게 과장하지 않는다. 예: 원문이 노출은 대체인지 보완인지 구분하지 않는다고 했는데 "내 일자리가 사라질까?"로 시작하면 틀린다.

[hook과 closing]
- hook은 원문에서 가장 놀라운 숫자나 사실을 질문이나 한 문장으로 던진다. "~연구입니다", "~를 분석했습니다" 같은 소개로 시작하지 않는다.
  원문 한계는 hook에 억지로 넣지 말고 바로 다음 원문 내용 장면에서 짚는다.
- closing은 원문 내용을 한 문장으로 정리하거나 시청자에게 질문을 던진다. 우리 해석은 closing에 넣지 않고 그 앞 interpretation 장면에 둔다.
- 해석 문장의 단서("~할 수 있다", "~가 도움이 될 수 있다")를 내레이션에서 지우지 않는다. "~이 전략이 됩니다" 같은 단정형으로 바꾸지 않는다.

{ACCURACY_RULES}"""
    prompt = f"""아래 분석과 해석으로 스토리보드를 쓰세요.

[분석 결과]
{analysis.model_dump_json(indent=2)}

[우리 해석]
{perspective.model_dump_json(indent=2)}"""
    return gemini_client.generate_json(prompt, Storyboard, system=system)
