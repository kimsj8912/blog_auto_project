from pathlib import Path

import pytest

from shorts.pipeline.schemas import (
    Analysis, Claim, Interpretation, Perspective, Scene, ScreenNumber, SourceNumber, Storyboard,
)
from shorts.pipeline.verify import normalize_text, numbers_in, quote_match, same_number, value_in_quote, verify

SOURCE = (Path(__file__).parent / "fixtures" / "sample_source.txt").read_text(encoding="utf-8")


def make_analysis(**overrides) -> Analysis:
    data = dict(
        title="Coordination Premiums in Small Teams",
        one_line_summary="자동화가 퍼지면 조정자가 전문가보다 상대적으로 더 받는다.",
        claims=[
            Claim(id="c1", statement="자동화가 퍼지면 조정자가 전문가보다 상대적으로 더 받는다. 절대 임금은 둘 다 떨어진다.",
                  quote="coordinators earn relatively more compared to specialists, although absolute wages for both groups decline.",
                  comparison="전문가 대비"),
            Claim(id="c2", statement="전문가는 밀려나지 않고 틈새시장으로 이동한다.",
                  quote="Specialists are not displaced; they move into niche markets", comparison=""),
        ],
        numbers=[
            SourceNumber(id="n1", value="2.41", meaning="조정자 보수", quote="coordinators earn 2.41 while specialists earn 4.15.",
                         setting="바깥 선택지 0.25", is_illustrative=True),
            SourceNumber(id="n2", value="4.15", meaning="전문가 보수", quote="coordinators earn 2.41 while specialists earn 4.15.",
                         setting="바깥 선택지 0.25", is_illustrative=True),
        ],
        caveats=["숫자는 모두 예시값이다."],
    )
    data.update(overrides)
    return Analysis(**data)


def make_perspective() -> Perspective:
    return Perspective(
        angle="조정 역량의 상대적 가치",
        interpretations=[Interpretation(id="i1", text="조율 경험을 쌓아 두면 도움이 될 수 있다.", based_on=["c1"])],
        takeaway="상대적 가치와 절대 가치를 구분하자.",
    )


def scene(index, purpose, narration="자동화가 퍼지면 조정자의 몫이 상대적으로 커집니다.", **kw) -> Scene:
    data = dict(index=index, purpose=purpose, narration=narration, on_screen_text=[], numbers=[],
                claim_ids=[], interpretation_ids=[], visual_intent="")
    data.update(kw)
    return Scene(**data)


def good_storyboard() -> Storyboard:
    return Storyboard(title="조정자의 상대 프리미엄", scenes=[
        scene(1, "hook", "자동화가 오면 누가 더 받을까요?", on_screen_text=["누가 더 받을까?"]),
        scene(2, "point", claim_ids=["c1"], on_screen_text=["전문가 대비 조정자 ↑"]),
        scene(3, "point", "모델 예시에서 조정자는 이 점 사일, 전문가는 사 점 일오를 받습니다.",
              claim_ids=["c1"],
              on_screen_text=["조정자 2.41 · 전문가 4.15", "예시값, 예측치 아님"],
              numbers=[ScreenNumber(display="2.41", source_number_id="n1", is_illustrative=True),
                       ScreenNumber(display="4.15", source_number_id="n2", is_illustrative=True)]),
        scene(4, "point", "전문가는 사라지지 않고 틈새시장으로 옮겨 갑니다.", claim_ids=["c2"],
              on_screen_text=["전문가 → 틈새시장"]),
        scene(5, "interpretation", "그래서 조율 경험을 쌓아 두면 도움이 될 수 있습니다.",
              interpretation_ids=["i1"], on_screen_text=["우리 해석", "조율 경험이 자산"]),
        scene(6, "closing", "상대적 가치와 절대 가치를 구분해 보세요.", on_screen_text=["상대 ≠ 절대"]),
    ])


def errors_of(report):
    return [i.message for i in report.issues if i.level == "error"]


# ── 도구 함수 ─────────────────────────────────────────


def test_normalize_joins_pdf_hyphenation_and_quotes():
    assert normalize_text("coordi-\n nators “earn”") == 'coordinators "earn"'


def test_numbers_in_and_same_number():
    assert numbers_in("1,000명 중 40%와 2.41") == ["1000", "40", "2.41"]
    assert same_number("40%", "40")
    assert same_number("1,000", "1000")
    assert not same_number("2.41", "2.4")


def test_quote_match_exact_near_and_missing():
    src = normalize_text(SOURCE)
    assert quote_match("Specialists are not displaced;", src) == 1.0
    near = "coordinators earn relatively more compared to the specialists, although absolute wages for both groups decline."
    assert 0.6 <= quote_match(near, src) < 1.0
    assert quote_match("Coordinators become the most valuable workers in the economy.", src) < 0.5


# ── 전체 검사 ─────────────────────────────────────────


def test_good_storyboard_has_no_errors():
    report = verify(SOURCE, make_analysis(), make_perspective(), good_storyboard())
    assert errors_of(report) == []
    # 상대 비교 claim을 쓴 장면은 사람 확인 항목으로 남는다.
    assert any(i.level == "check" and "상대 비교" in i.message for i in report.issues)


def test_invented_quote_is_error():
    analysis = make_analysis()
    analysis.claims[1].quote = "Specialists become unemployed."
    report = verify(SOURCE, analysis, make_perspective(), good_storyboard())
    assert any("인용을 원문에서 찾지 못했습니다" in m for m in errors_of(report))


def test_screen_number_mismatch_is_error():
    sb = good_storyboard()
    sb.scenes[2].numbers[0].display = "2.4"
    sb.scenes[2].on_screen_text[0] = "조정자 2.4 · 전문가 4.15"
    report = verify(SOURCE, make_analysis(), make_perspective(), sb)
    assert any("원문 값 '2.41'" in m for m in errors_of(report))


def test_undeclared_screen_number_is_error():
    sb = good_storyboard()
    sb.scenes[1].on_screen_text = ["조정자 몫 10배"]
    report = verify(SOURCE, make_analysis(), make_perspective(), sb)
    assert any("'10'의 출처" in m for m in errors_of(report))


def test_illustrative_without_label_is_error():
    sb = good_storyboard()
    sb.scenes[2].on_screen_text = ["조정자 2.41 · 전문가 4.15"]
    report = verify(SOURCE, make_analysis(), make_perspective(), sb)
    assert any("예시값" in m for m in errors_of(report))


def test_interpretation_without_label_is_error():
    sb = good_storyboard()
    sb.scenes[4].on_screen_text = ["조율 경험이 자산"]
    report = verify(SOURCE, make_analysis(), make_perspective(), sb)
    assert any("우리 해석" in m for m in errors_of(report))


def test_digits_in_narration_is_error():
    sb = good_storyboard()
    sb.scenes[2].narration = "조정자는 2.41을 받습니다."
    report = verify(SOURCE, make_analysis(), make_perspective(), sb)
    assert any("아라비아 숫자" in m for m in errors_of(report))


def test_unknown_references_are_errors():
    sb = good_storyboard()
    sb.scenes[1].claim_ids = ["c9"]
    sb.scenes[4].interpretation_ids = ["i9"]
    report = verify(SOURCE, make_analysis(), make_perspective(), sb)
    errs = errors_of(report)
    assert any("'c9'" in m for m in errs) and any("'i9'" in m for m in errs)


def test_too_long_is_error():
    sb = good_storyboard()
    for s in sb.scenes:
        s.narration = "가" * 120
    report = verify(SOURCE, make_analysis(), make_perspective(), sb)
    assert any("넘습니다" in m for m in errors_of(report))


def test_mixed_settings_warns():
    analysis = make_analysis()
    analysis.numbers[1].setting = "바깥 선택지 1"
    report = verify(SOURCE, analysis, make_perspective(), good_storyboard())
    assert any(i.level == "warning" and "설정" in i.message for i in report.issues)


@pytest.mark.parametrize("value", ["9.99"])
def test_source_number_not_in_quote_is_error(value):
    analysis = make_analysis()
    analysis.numbers[0].value = value
    report = verify(SOURCE, analysis, make_perspective(), good_storyboard())
    assert any("인용 구절 안에 없습니다" in m for m in errors_of(report))


@pytest.mark.parametrize("value", ["47 and 56%", "47~56%"])
def test_range_value_in_quote(value):
    assert value_in_quote(value, "this share increases to between 47 and 56% of all tasks.")


def test_range_value_with_wrong_end_is_not_in_quote():
    assert not value_in_quote("47 and 60%", "between 47 and 56% of all tasks.")
