"""5단계 자막 표기·화면 문구 시각."""
import pytest

from shorts.voice import sync


def words(text: str) -> list[dict]:
    return [{"text": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(text.split())]


@pytest.mark.parametrize("text,value", [
    ("십", 10), ("팔십", 80), ("사십칠", 47), ("오십육", 56), ("백", 100), ("이천이십육", 2026), ("만", 10000),
])
def test_parse_sino(text, value):
    assert sync.parse_sino(text) == value


@pytest.mark.parametrize("text", ["사오", "가나", ""])
def test_parse_sino_rejects_non_numerals(text):
    assert sync.parse_sino(text) is None


def test_captions_use_screen_notation():
    w = words("미국 근로자의 팔십 퍼센트는 업무의 최소 십 퍼센트가 영향받을 수 있다")
    caps = sync.caption_words(w, ["미국 근로자 80%", "업무 최소 10%"], ["80%", "10%"])
    assert " ".join(c for c in caps if c) == "미국 근로자의 80%는 업무의 최소 10%가 영향받을 수 있다"


def test_range_and_acronym():
    w = words("엘엘엠 단독은 약 십오 퍼센트지만, 사십칠에서 오십육 퍼센트로 늘어납니다.")
    caps = sync.caption_words(w, ["LLM 단독 15%", "47~56%"], ["15%", "47 and 56%"])
    assert " ".join(c for c in caps if c) == "LLM 단독은 약 15%지만, 47에서 56%로 늘어납니다."


def test_only_screen_numbers_are_converted():
    # 화면에 없는 숫자, 숫자처럼 보이는 낱말('이', '사고')은 그대로 둔다.
    w = words("이 분석에서 비판적 사고 오십 퍼센트")
    caps = sync.caption_words(w, ["비판적 사고"], [])
    assert caps == [x["text"] for x in w]


def test_decimal_number():
    w = words("이점사일을 받습니다")
    assert sync.caption_words(w, ["2.41"], ["2.41"])[0] == "2.41을"


def test_screen_cues_follow_spoken_words():
    w = words("엘엘엠 단독은 약 십오 퍼센트지만, 도구를 통합하면 사십칠에서 오십육 퍼센트로 늘어납니다.")
    lines = ["LLM 단독 활용 시: 15%", "도구 통합 시: 47~56%"]
    caps = sync.caption_words(w, lines, ["15%", "47 and 56%"])
    cues = sync.screen_cues(lines, w, caps)
    assert cues == [0.0, 2.5]  # LLM(0번째 단어), 도구를(5번째 단어)


def test_interpretation_label_shows_first_and_missing_line_is_none():
    w = words("모델을 넘어 도구를 다루는 능력이 중요할 수 있습니다.")
    lines = ["우리 해석", "도구 활용 역량", "전혀 다른 문구"]
    cues = sync.screen_cues(lines, w, [x["text"] for x in w])
    assert cues == [0.0, 1.0, None]


def test_cues_keep_line_order():
    w = words("도구 이야기 먼저 하고 모델 이야기")
    cues = sync.screen_cues(["모델", "도구"], w, [x["text"] for x in w])
    assert cues == [2.0, None]  # '도구'는 '모델' 앞에만 있으니 순서상 못 찾는다
