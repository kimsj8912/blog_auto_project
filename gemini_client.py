"""Gemini 호출 공용 모듈.

블로그 원고(content_generator.py)와 숏츠 대본 파이프라인(shorts/pipeline)이 같이 쓴다.
서버 과부하(503) 같은 일시적 오류는 SDK가 지수 백오프로 다시 시도하고,
기본 모델이 끝내 실패하면 대체 모델로 넘어간다.
"""
import os
from typing import TypeVar

from dotenv import load_dotenv
from google.genai import Client, errors, types
from pydantic import BaseModel

load_dotenv()

# 1초, 2초, 4초, 8초... 간격(최대 60초)으로 첫 호출 포함 5번까지 시도한다.
RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=5,
    initial_delay=1.0,
    max_delay=60.0,
    exp_base=2,
    http_status_codes=[408, 429, 500, 502, 503, 504],
)

# 앞의 모델이 재시도 후에도 실패하면 다음 모델로 넘어간다.
MODEL_IDS = ["gemini-3.5-flash", "gemini-2.5-flash"]

_client = None

T = TypeVar("T", bound=BaseModel)


def get_client():
    """처음 호출할 때 클라이언트를 만든다(키 없이 import만 해도 오류가 나지 않게)."""
    global _client
    if _client is None:
        _client = Client(
            api_key=os.getenv("GEMINI_API_KEY"),
            http_options=types.HttpOptions(retry_options=RETRY_OPTIONS),
        )
    return _client


def _call(contents, config=None):
    last_error = None
    for model_id in MODEL_IDS:
        try:
            return get_client().models.generate_content(
                model=model_id, contents=contents, config=config
            )
        except errors.APIError as e:
            print(f"⚠️ [{model_id}] 호출 실패 ({e.code}): {e.message}")
            last_error = e
    raise last_error


def generate(prompt):
    """Gemini로 글을 생성한다. 기본 모델이 계속 실패하면 대체 모델을 쓴다."""
    return _call(prompt).text


def generate_json(prompt: str, schema: type[T], system: str | None = None) -> T:
    """Pydantic 스키마로 구조화 출력을 받아 검증된 객체로 돌려준다."""
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=schema,
    )
    response = _call(prompt, config)
    if isinstance(response.parsed, schema):
        return response.parsed
    # SDK가 파싱하지 못한 경우 원문 JSON을 직접 검증한다.
    return schema.model_validate_json(response.text)
