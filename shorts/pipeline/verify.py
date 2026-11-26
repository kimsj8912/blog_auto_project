"""원문 대조 검사.

LLM이 만든 분석·스토리보드를 원문과 맞춰 보고 문제를 모은다. 이 검사는 사람의 원문 대조를
대신하지 않는다. 기계로 잡을 수 있는 것(인용·숫자·표기·길이·해석 표시)을 먼저 걸러 내고,
사람이 확인해야 할 지점을 짚어 준다.
"""
import re
from dataclasses import asdict, dataclass
from typing import Literal

from . import timing
from .schemas import Analysis, Perspective, Storyboard

Level = Literal["error", "warning", "check"]

INTERPRETATION_LABEL = "우리 해석"
ILLUSTRATIVE_LABEL = "예시값"

# 인용이 원문과 "거의" 같다고 볼 기준: 인용의 단어 묶음 중 이 비율 이상이 원문에 있으면 경고만 한다.
NEAR_MATCH_RATIO = 0.6
SHINGLE = 3


@dataclass
class Issue:
    level: Level
    where: str
    message: str


@dataclass
class Report:
    issues: list[Issue]
    estimated_seconds: float

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "estimated_seconds": round(self.estimated_seconds, 1),
            "issues": [asdict(i) for i in self.issues],
        }


# ── 정규화 도구 ───────────────────────────────────────

_QUOTE_MAP = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", " ": " "})


def normalize_text(text: str) -> str:
    text = text.translate(_QUOTE_MAP)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # PDF 줄끝 하이픈
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


def numbers_in(text: str) -> list[str]:
    """문자열 속 숫자 토큰. 천 단위 쉼표는 지운다."""
    return [tok.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", tok) else tok
            for tok in _NUMBER_RE.findall(text)]


def _as_float(token: str) -> float | None:
    try:
        return float(token.replace(",", ""))
    except ValueError:
        return None


def same_number(a: str, b: str) -> bool:
    """두 표기 속 숫자가 같은지. '40%'와 '40', '1,000'과 '1000'은 같다고 본다."""
    na, nb = numbers_in(a), numbers_in(b)
    if not na or len(na) != len(nb):
        return False
    return all(_as_float(x) == _as_float(y) for x, y in zip(na, nb))


def value_in_quote(value: str, quote: str) -> bool:
    """값 속 숫자가 모두 인용 구절에 있는지. '47 and 56%' 같은 범위도 숫자마다 본다."""
    wanted = numbers_in(value)
    have = [_as_float(t) for t in numbers_in(quote)]
    return bool(wanted) and all(_as_float(w) in have for w in wanted)


def quote_match(quote: str, source_norm: str) -> float:
    """인용이 원문에 있는 정도(0~1). 1이면 그대로 있다."""
    q = normalize_text(quote)
    if not q:
        return 0.0
    if q in source_norm:
        return 1.0
    words = _words(q)
    if len(words) < SHINGLE:
        return 0.0
    source_words = " " + " ".join(_words(source_norm)) + " "
    shingles = [" ".join(words[i:i + SHINGLE]) for i in range(len(words) - SHINGLE + 1)]
    return sum(f" {s} " in source_words for s in shingles) / len(shingles)


def _words(text: str) -> list[str]:
    return re.findall(r"[\w.%]+", text)


# ── 검사 ─────────────────────────────────────────────


def verify(source_text: str, analysis: Analysis, perspective: Perspective,
           storyboard: Storyboard) -> Report:
    issues: list[Issue] = []
    add = lambda level, where, msg: issues.append(Issue(level, where, msg))  # noqa: E731
    source_norm = normalize_text(source_text)

    claims = {c.id: c for c in analysis.claims}
    numbers = {n.id: n for n in analysis.numbers}
    interps = {i.id: i for i in perspective.interpretations}

    # 1. 분석 결과의 인용과 숫자가 원문에 있는가
    for c in analysis.claims:
        _check_quote(add, f"분석 {c.id}", c.quote, source_norm)
    for n in analysis.numbers:
        _check_quote(add, f"숫자 {n.id}", n.quote, source_norm)
        if not value_in_quote(n.value, n.quote):
            add("error", f"숫자 {n.id}", f"값 '{n.value}'이(가) 인용 구절 안에 없습니다.")

    # 2. 해석은 실제 claim에 근거하는가
    for i in perspective.interpretations:
        if not i.based_on:
            add("error", f"해석 {i.id}", "근거 claim이 없습니다.")
        for cid in i.based_on:
            if cid not in claims:
                add("error", f"해석 {i.id}", f"없는 claim '{cid}'을(를) 근거로 듭니다.")

    # 3. 장면별 검사
    scenes = storyboard.scenes
    for s in scenes:
        where = f"장면 {s.index}"
        screen = "\n".join(s.on_screen_text)

        _check_narration(add, where, s.narration)

        for cid in s.claim_ids:
            if cid not in claims:
                add("error", where, f"없는 claim '{cid}'을(를) 참조합니다.")
            elif claims[cid].comparison:
                add("check", where,
                    f"{cid}는 상대 비교({claims[cid].comparison})입니다. "
                    "내레이션·화면이 비교 대상 없이 절대적 주장처럼 들리지 않는지 확인하세요.")
        for iid in s.interpretation_ids:
            if iid not in interps:
                add("error", where, f"없는 해석 '{iid}'을(를) 참조합니다.")

        # 해석 표시
        uses_interp = s.purpose == "interpretation" or bool(s.interpretation_ids)
        if uses_interp:
            if not s.on_screen_text or not s.on_screen_text[0].strip().startswith(INTERPRETATION_LABEL):
                add("error", where, f"해석 장면인데 화면 첫 줄에 '{INTERPRETATION_LABEL}' 표시가 없습니다.")
            if s.purpose != "interpretation":
                add("warning", where, "해석을 쓰는데 purpose가 interpretation이 아닙니다.")
        elif s.purpose in ("context", "point") and not s.claim_ids:
            add("warning", where, "원문 내용 장면인데 근거 claim이 없습니다.")

        # 숫자
        declared = [tok for sn in s.numbers for tok in numbers_in(sn.display)]
        for tok in numbers_in(screen):
            if not any(_as_float(tok) == _as_float(d) for d in declared):
                add("error", where, f"화면 숫자 '{tok}'의 출처가 numbers에 적혀 있지 않습니다.")

        settings = set()
        needs_illustrative_label = False
        for sn in s.numbers:
            if sn.source_number_id:
                src = numbers.get(sn.source_number_id)
                if src is None:
                    add("error", where, f"없는 숫자 '{sn.source_number_id}'을(를) 참조합니다.")
                    continue
                if not same_number(sn.display, src.value):
                    add("error", where,
                        f"화면 숫자 '{sn.display}'이(가) 원문 값 '{src.value}'({src.id})와 다릅니다.")
                if src.setting:
                    settings.add(src.setting)
                if src.is_illustrative:
                    needs_illustrative_label = True
            elif not sn.is_illustrative:
                add("error", where, f"화면 숫자 '{sn.display}'에 원문 출처가 없습니다.")
            if sn.is_illustrative:
                needs_illustrative_label = True
        if needs_illustrative_label and ILLUSTRATIVE_LABEL not in screen:
            add("error", where, f"예시값을 쓰는데 화면에 '{ILLUSTRATIVE_LABEL}, 예측치 아님' 표시가 없습니다.")
        if len(settings) > 1:
            add("warning", where,
                "서로 다른 설정의 숫자가 한 장면에 섞였습니다: " + " / ".join(sorted(settings)))

    # 4. 구성과 길이
    if not timing.MIN_SCENES <= len(scenes) <= timing.MAX_SCENES:
        add("warning", "구성", f"장면이 {len(scenes)}개입니다(권장 {timing.MIN_SCENES}~{timing.MAX_SCENES}개).")
    if scenes and scenes[0].purpose != "hook":
        add("warning", "구성", "첫 장면이 hook이 아닙니다.")
    if scenes and scenes[-1].purpose != "closing":
        add("warning", "구성", "마지막 장면이 closing이 아닙니다.")
    if [s.index for s in scenes] != list(range(1, len(scenes) + 1)):
        add("warning", "구성", "장면 번호가 1부터 차례대로가 아닙니다.")

    seconds = timing.estimate_seconds([s.narration for s in scenes])
    low, high = timing.TARGET_SECONDS
    if seconds > timing.HARD_MAX_SECONDS:
        add("error", "길이", f"예상 길이 {seconds:.0f}초로 {timing.HARD_MAX_SECONDS}초를 넘습니다.")
    elif not low <= seconds <= high:
        add("warning", "길이", f"예상 길이 {seconds:.0f}초(목표 {low}~{high}초).")

    return Report(issues=issues, estimated_seconds=seconds)


def _check_quote(add, where: str, quote: str, source_norm: str) -> None:
    ratio = quote_match(quote, source_norm)
    if ratio == 1.0:
        return
    if ratio >= NEAR_MATCH_RATIO:
        add("warning", where, f"인용이 원문과 조금 다릅니다(일치 {ratio:.0%}). 원문 그대로인지 확인하세요.")
    else:
        add("error", where, f"인용을 원문에서 찾지 못했습니다(일치 {ratio:.0%}): \"{quote[:80]}\"")


def _check_narration(add, where: str, narration: str) -> None:
    if re.search(r"\d", narration):
        add("error", where, "내레이션에 아라비아 숫자가 있습니다. 읽는 소리대로 적어야 합니다(예: 10배 → 열 배).")
    latin = re.findall(r"[A-Za-z]+", narration)
    if latin:
        add("warning", where, "내레이션에 영문이 있습니다(TTS 오독 주의): " + ", ".join(sorted(set(latin))))
