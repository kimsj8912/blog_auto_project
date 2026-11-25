"""대본 단계의 입출력 스키마.

Gemini 구조화 출력(response_schema)에 그대로 넘기므로 기본값·복잡한 검증기는 두지 않는다.
"""
from typing import Literal

from pydantic import BaseModel, Field


# ── 원문 ──────────────────────────────────────────────


class SourceDoc(BaseModel):
    """읽어 들인 원문. LLM 출력이 아니라 sources.py가 만든다."""

    origin: str = Field(description="파일 경로나 웹 주소")
    title: str
    text: str


# ── 1. 분석 ───────────────────────────────────────────


class Claim(BaseModel):
    id: str = Field(description="c1, c2... 처럼 붙이는 식별자")
    statement: str = Field(description="원문이 말하는 내용을 한국어로 정확히 옮긴 문장")
    quote: str = Field(description="근거가 되는 원문 구절을 원문 언어 그대로 한 글자도 바꾸지 않고 복사")
    comparison: str = Field(
        description="상대 비교라면 무엇과 비교한 것인지(예: '전문가 대비'). 절대적 주장이면 빈 문자열"
    )


class SourceNumber(BaseModel):
    id: str = Field(description="n1, n2... 처럼 붙이는 식별자")
    value: str = Field(description="원문에 적힌 숫자 표기 그대로(예: '2.41', '40%')")
    meaning: str = Field(description="이 숫자가 무엇을 뜻하는지 한국어로")
    quote: str = Field(description="이 숫자가 들어 있는 원문 구절을 그대로 복사")
    setting: str = Field(description="이 숫자가 나온 조건·실험 설정. 특별한 조건이 없으면 빈 문자열")
    is_illustrative: bool = Field(description="이론 모델의 예시값이면 true, 실측·예측치면 false")


class Analysis(BaseModel):
    title: str = Field(description="원문 제목")
    one_line_summary: str
    claims: list[Claim]
    numbers: list[SourceNumber]
    caveats: list[str] = Field(description="원문이 밝힌 한계나 오해하기 쉬운 지점")


# ── 2. 관점 해석 ──────────────────────────────────────


class Interpretation(BaseModel):
    id: str = Field(description="i1, i2... 처럼 붙이는 식별자")
    text: str = Field(description="우리 관점의 해석. 원문 내용처럼 쓰지 않는다")
    based_on: list[str] = Field(description="근거가 되는 claim id 목록")


class Perspective(BaseModel):
    angle: str = Field(description="이 원문을 어떤 각도로 풀지 한 문장")
    interpretations: list[Interpretation]
    takeaway: str = Field(description="시청자가 가져갈 한 문장")


# ── 3. 스토리보드 ─────────────────────────────────────


class ScreenNumber(BaseModel):
    display: str = Field(description="화면에 보이는 숫자 표기(예: '2.41', '40%')")
    source_number_id: str = Field(description="analysis.numbers의 id. 원문 숫자가 아니면 빈 문자열")
    is_illustrative: bool = Field(description="예시값이면 true")


class Scene(BaseModel):
    index: int
    purpose: Literal["hook", "context", "point", "interpretation", "closing"]
    narration: str = Field(description="더빙할 문장. 숫자·영문은 읽는 소리대로 한글로 적는다")
    on_screen_text: list[str] = Field(description="화면에 나오는 문구. 짧게")
    numbers: list[ScreenNumber] = Field(description="화면에 나오는 숫자 전부")
    claim_ids: list[str] = Field(description="이 장면이 근거로 삼는 claim id")
    interpretation_ids: list[str] = Field(description="이 장면이 쓰는 interpretation id")
    visual_intent: str = Field(description="화면 연출 의도. 장면 코드를 쓸 사람이 읽는다")


class Storyboard(BaseModel):
    title: str
    scenes: list[Scene]
