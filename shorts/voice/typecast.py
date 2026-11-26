"""Typecast 음성 합성(타임스탬프 포함) 호출.

POST /v1/text-to-speech/with-timestamps 는 base64 음성과 단어·글자 단위 시각(초)을 JSON으로 돌려준다.
"""
import base64
import os
import time
from dataclasses import dataclass, field

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.typecast.ai"
ENDPOINT = f"{API}/v1/text-to-speech/with-timestamps"
MAX_TEXT = 2000
RETRY_STATUS = {429, 500, 502, 503, 504}

ERROR_HINTS = {
    401: "API 키가 틀렸습니다(TYPECAST_API_KEY).",
    402: "크레딧이 부족하거나 계정이 비활성 상태입니다.",
    404: "목소리를 찾지 못했거나 이 모델을 지원하지 않습니다(TYPECAST_VOICE_ID, TYPECAST_MODEL).",
    422: "합성할 수 없는 글자가 대본에 있습니다.",
    429: "요청이 너무 많습니다. 잠시 뒤 다시 실행하세요.",
}


class TypecastError(RuntimeError):
    pass


@dataclass
class Settings:
    api_key: str
    voice_id: str
    model: str = "ssfm-v30"
    tempo: float = 1.0
    pitch: int = 0

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [k for k in ("TYPECAST_API_KEY", "TYPECAST_VOICE_ID") if not os.getenv(k)]
        if missing:
            raise TypecastError(".env에 " + ", ".join(missing) + "이(가) 비어 있습니다.")
        return cls(
            api_key=os.environ["TYPECAST_API_KEY"],
            voice_id=os.environ["TYPECAST_VOICE_ID"],
            model=os.getenv("TYPECAST_MODEL") or "ssfm-v30",
            tempo=float(os.getenv("TYPECAST_TEMPO") or 1.0),
            pitch=int(os.getenv("TYPECAST_PITCH") or 0),
        )


@dataclass
class Segment:
    text: str
    start: float
    end: float


@dataclass
class Speech:
    audio: bytes
    audio_format: str
    duration: float
    words: list[Segment] = field(default_factory=list)
    characters: list[Segment] = field(default_factory=list)


def build_body(settings: Settings, text: str, previous_text: str = "", next_text: str = "") -> dict:
    if not 1 <= len(text) <= MAX_TEXT:
        raise TypecastError(f"대본은 1~{MAX_TEXT}자여야 합니다(지금 {len(text)}자).")
    body = {
        "voice_id": settings.voice_id,
        "text": text,
        "model": settings.model,
        "language": "kor",
        "output": {"audio_tempo": settings.tempo, "audio_pitch": settings.pitch, "audio_format": "wav"},
    }
    # v30 이상은 앞뒤 문맥을 주면 장면 사이 억양이 자연스럽게 이어진다.
    if settings.model != "ssfm-v21":
        body["prompt"] = {"emotion_type": "smart",
                          "previous_text": previous_text[:MAX_TEXT], "next_text": next_text[:MAX_TEXT]}
    return body


def parse_response(data: dict) -> Speech:
    def segs(items):
        return [Segment(text=i["text"], start=float(i["start"]), end=float(i["end"])) for i in items or []]

    return Speech(
        audio=base64.b64decode(data["audio"]),
        audio_format=data.get("audio_format", "wav"),
        duration=float(data["audio_duration"]),
        words=segs(data.get("words")),
        characters=segs(data.get("characters")),
    )


def synthesize(settings: Settings, text: str, previous_text: str = "", next_text: str = "",
               attempts: int = 3, session=requests) -> Speech:
    body = build_body(settings, text, previous_text, next_text)
    headers = {"X-API-KEY": settings.api_key, "Content-Type": "application/json"}
    for attempt in range(1, attempts + 1):
        resp = session.post(ENDPOINT, json=body, headers=headers, timeout=120)
        if resp.status_code == 200:
            return parse_response(resp.json())
        if resp.status_code in RETRY_STATUS and attempt < attempts:
            wait = attempt * 5
            print(f"  … {resp.status_code}, {wait}초 뒤 다시 시도")
            time.sleep(wait)
            continue
        raise TypecastError(_explain(resp))
    raise TypecastError("음성 합성에 실패했습니다.")


def _explain(resp) -> str:
    try:
        data = resp.json()
        detail = data.get("message") or data.get("detail") or ""
        code = data.get("error_code") or ""
    except ValueError:
        detail, code = resp.text[:200], ""
    hint = ERROR_HINTS.get(resp.status_code, "")
    return f"Typecast {resp.status_code} {code} {detail} {hint}".strip()
