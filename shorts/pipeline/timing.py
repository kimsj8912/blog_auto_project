"""영상 길이 추정. 실제 길이는 3단계(Typecast 음성)에서 정해지므로 여기서는 대략만 본다."""

TARGET_SECONDS = (50, 60)
HARD_MAX_SECONDS = 65
MIN_SCENES, MAX_SCENES = 5, 8

# Typecast ssfm-v30·속도 0.9 실측(2026-11-26, 6장면 261자/음성 44.9초)으로 초당 약 5.8음절(공백 제외).
CHARS_PER_SECOND = 5.8
# 원형 작업에서 정한 장면 앞뒤 여백: 말 시작 전 0.6초, 끝난 뒤 0.9초.
SCENE_PADDING_SECONDS = 0.6 + 0.9

TYPICAL_SCENES = 6


def speech_chars(text: str) -> int:
    return len("".join(text.split()))


def estimate_seconds(narrations: list[str]) -> float:
    speech = sum(speech_chars(n) for n in narrations) / CHARS_PER_SECOND
    return speech + SCENE_PADDING_SECONDS * len(narrations)


def target_chars_low() -> int:
    return int((TARGET_SECONDS[0] - SCENE_PADDING_SECONDS * TYPICAL_SCENES) * CHARS_PER_SECOND)


def target_chars_high() -> int:
    return int((TARGET_SECONDS[1] - SCENE_PADDING_SECONDS * TYPICAL_SCENES) * CHARS_PER_SECOND)
