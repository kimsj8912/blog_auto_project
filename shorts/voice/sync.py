"""5단계 자막·동기화: 단어 시각을 화면에 맞게 다듬는다.

1. 자막 표기: 내레이션은 TTS용으로 숫자·영문을 한글로 적는다("사십칠 퍼센트", "엘엘엠").
   자막에는 화면 표기("47%", "LLM")를 보여 준다. 잘못 바꾸지 않도록
   - 숫자는 그 장면 화면에 나오는 숫자(2단계 verify.py가 원문과 대조한 값)일 때만 바꾸고,
   - 영문은 그 장면 화면 문구에 있는 대문자 약어(LLM, AI 등)일 때만 바꾼다.
2. 화면 문구 시각: on_screen_text 각 줄이 처음 들리는 단어의 시각(말 시작 기준 초)을 찾는다.
   영상 단계는 그 시각에 줄을 띄운다. 못 찾은 줄은 None이고 영상 단계가 앞 줄 뒤에 띄운다.
"""
import re

from shorts.pipeline.verify import numbers_in

INTERPRETATION_LABEL = "우리 해석"

_DIGITS = {"영": 0, "공": 0, "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9}
_SMALL_UNITS = {"십": 10, "백": 100, "천": 1000}
_NUMERAL_RE = re.compile(r"^([영공일이삼사오육칠팔구십백천만]+)(?:점([영공일이삼사오육칠팔구]+))?(.*)$")
PERCENT = "퍼센트"

LETTER_NAMES = {
    "A": "에이", "B": "비", "C": "씨", "D": "디", "E": "이", "F": "에프", "G": "지", "H": "에이치",
    "I": "아이", "J": "제이", "K": "케이", "L": "엘", "M": "엠", "N": "엔", "O": "오", "P": "피",
    "Q": "큐", "R": "알", "S": "에스", "T": "티", "U": "유", "V": "브이", "W": "더블유", "X": "엑스",
    "Y": "와이", "Z": "지",
}


def parse_sino(text: str) -> int | None:
    """한자어 수사를 정수로. '사십칠' → 47, '십' → 10, '이천이십육' → 2026. 수사가 아니면 None."""
    if not text:
        return None
    total, section, digit = 0, 0, None
    for ch in text:
        if ch in _DIGITS:
            if digit is not None:  # '사오'처럼 숫자가 연달아 나오면 수사가 아니다
                return None
            digit = _DIGITS[ch]
        elif ch in _SMALL_UNITS:
            section += (1 if digit is None else digit) * _SMALL_UNITS[ch]
            digit = None
        elif ch == "만":
            section += digit or 0
            total += (section or 1) * 10_000
            section, digit = 0, None
        else:
            return None
    return total + section + (digit or 0)


def _fraction(text: str) -> str | None:
    out = []
    for ch in text:
        if ch not in _DIGITS:
            return None
        out.append(str(_DIGITS[ch]))
    return "".join(out)


def _fmt(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


def read_number(word: str) -> tuple[float, str] | None:
    """단어 앞의 수사를 (값, 나머지)로. '사십칠에서' → (47, '에서'), '이 점 사일'은 단어가 나뉘어 다루지 않는다."""
    m = _NUMERAL_RE.match(word)
    if not m:
        return None
    whole = parse_sino(m.group(1))
    if whole is None:
        return None
    value = float(whole)
    if m.group(2):
        frac = _fraction(m.group(2))
        if frac is None:
            return None
        value = float(f"{whole}.{frac}")
    return value, m.group(3)


def acronym_reading(acronym: str) -> str:
    return "".join(LETTER_NAMES.get(ch, "") for ch in acronym.upper())


def screen_acronyms(lines: list[str]) -> dict[str, str]:
    """화면 문구 속 대문자 약어 → 한글 읽기. {'엘엘엠': 'LLM'}"""
    found = {}
    for line in lines:
        for tok in re.findall(r"\b[A-Z]{2,}\b", line):
            found[acronym_reading(tok)] = tok
    return found


def caption_words(words: list[dict], screen_lines: list[str], screen_numbers: list[str]) -> list[str]:
    """단어마다 자막 표기. 앞 단어에 붙어 사라지는 단어는 빈 문자열."""
    allowed = {float(t) for s in list(screen_numbers) + list(screen_lines) for t in numbers_in(s)}
    acronyms = screen_acronyms(screen_lines)
    out = [w["text"] for w in words]
    i = 0
    while i < len(words):
        text = words[i]["text"]
        for reading, acro in sorted(acronyms.items(), key=lambda kv: -len(kv[0])):
            if text.startswith(reading):
                out[i] = acro + text[len(reading):]
                break
        else:
            hit = read_number(text)
            if hit and hit[0] in allowed:
                num, rest = _fmt(hit[0]), hit[1]
                if rest.startswith(PERCENT):
                    out[i] = num + "%" + rest[len(PERCENT):]
                elif not rest and i + 1 < len(words) and words[i + 1]["text"].startswith(PERCENT):
                    out[i] = num + "%" + words[i + 1]["text"][len(PERCENT):]
                    out[i + 1] = ""
                    i += 1
                else:
                    out[i] = num + rest
        i += 1
    return out


# ── 화면 문구 시각 ──────────────────────────────────


def _keys(line: str) -> list[str]:
    """줄에서 들릴 만한 낱말. 한글은 조사가 붙어도 맞도록 앞 두 글자만 쓴다."""
    keys = []
    for tok in re.findall(r"\d+(?:\.\d+)?|[A-Za-z]{2,}|[가-힣]{2,}", line):
        keys.append(tok[:2] if re.match(r"[가-힣]", tok) else tok)
    return keys


def _matches(key: str, caption: str) -> bool:
    if re.fullmatch(r"\d+(?:\.\d+)?", key):
        return any(float(t) == float(key) for t in numbers_in(caption))
    if re.fullmatch(r"[A-Za-z]+", key):
        return key.lower() in caption.lower()
    return caption.startswith(key)


def screen_cues(lines: list[str], words: list[dict], captions: list[str]) -> list[float | None]:
    """줄마다 처음 들리는 단어의 시작 시각(말 시작 기준 초). 줄 순서는 지킨다."""
    cues: list[float | None] = []
    pos = 0
    for n, line in enumerate(lines):
        if n == 0 and line.strip().startswith(INTERPRETATION_LABEL):
            cues.append(0.0)
            continue
        keys = _keys(line)
        hit = None
        for j in range(pos, len(words)):
            cap = captions[j] or words[j]["text"]
            if any(_matches(k, cap) for k in keys):
                hit = j
                break
        if hit is None:
            cues.append(None)
        else:
            cues.append(round(float(words[hit]["start"]), 3))
            pos = hit + 1
    return cues


def annotate(entry: dict, on_screen_text: list[str], screen_numbers: list[str]) -> dict:
    """voice.json 장면 항목에 단어별 caption과 screen_cues를 채운다."""
    captions = caption_words(entry["words"], on_screen_text, screen_numbers)
    for w, c in zip(entry["words"], captions):
        w["caption"] = c
    entry["screen_cues"] = screen_cues(on_screen_text, entry["words"], captions)
    return entry
