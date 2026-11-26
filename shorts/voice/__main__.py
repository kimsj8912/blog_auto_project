"""음성 단계 실행: storyboard.json의 장면별 내레이션을 Typecast로 합성한다.

    python -m shorts.voice --run-dir .local/runs/<폴더>              # 아직 없는 장면만
    python -m shorts.voice --run-dir .local/runs/<폴더> --only 2,5   # 특정 장면만 다시
    python -m shorts.voice --run-dir .local/runs/<폴더> --force      # 전부 다시
    python -m shorts.voice --run-dir .local/runs/<폴더> --sample     # 장면 1만 미리 듣기

결과: <run-dir>/audio/sceneN.wav, <run-dir>/voice.json(장면별 길이와 단어 시각).
다시 만들 때마다 크레딧이 들므로 기본은 없는 장면만 만든다.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from shorts.pipeline import timing
from shorts.pipeline.schemas import Storyboard

from . import typecast

LEAD_IN, TAIL = 0.6, 0.9  # 장면 앞뒤 여백(초). timing.SCENE_PADDING_SECONDS와 같다.


def _letters(text: str) -> str:
    return re.sub(r"[\W_]+", "", text)


def text_coverage(narration: str, words: list[typecast.Segment]) -> float:
    """단어 시각에 잡힌 글자가 내레이션 글자의 몇 %인지. 1보다 많이 낮으면 일부를 건너뛴 것이다."""
    want = _letters(narration)
    got = _letters("".join(w.text for w in words))
    return min(len(got) / len(want), 1.0) if want else 1.0


def scene_entry(index: int, narration: str, file: str, speech: typecast.Speech) -> dict:
    return {
        "index": index,
        "file": file,
        "narration": narration,
        "audio_seconds": round(speech.duration, 3),
        "estimated_seconds": round(timing.speech_chars(narration) / timing.CHARS_PER_SECOND, 2),
        # 장면 길이는 음성 길이에 맞춘다: 말 시작 전 LEAD_IN, 끝난 뒤 TAIL.
        "scene_seconds": round(LEAD_IN + speech.duration + TAIL, 3),
        "speech_start": LEAD_IN,
        "text_coverage": round(text_coverage(narration, speech.words), 3),
        "words": [{"text": w.text, "start": w.start, "end": w.end} for w in speech.words],
    }


def main(argv=None, session=None) -> int:
    p = argparse.ArgumentParser(prog="python -m shorts.voice", description="스토리보드 → 장면별 음성과 단어 시각")
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--only", help="이 장면만 다시 만든다(쉼표로 구분, 예: 2,5)")
    p.add_argument("--force", action="store_true", help="있는 장면도 전부 다시 만든다")
    p.add_argument("--sample", action="store_true", help="장면 1만 voice_sample.wav로 만든다")
    args = p.parse_args(argv)

    sb_path = args.run_dir / "storyboard.json"
    if not sb_path.exists():
        sys.exit(f"❌ {sb_path}가 없습니다. 먼저 python -m shorts.pipeline 을 실행하세요.")
    storyboard = Storyboard.model_validate_json(sb_path.read_text(encoding="utf-8"))
    scenes = storyboard.scenes

    try:
        settings = typecast.Settings.from_env()
    except typecast.TypecastError as e:
        sys.exit(f"❌ {e}")
    kwargs = {"session": session} if session is not None else {}

    audio_dir = args.run_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    voice_path = args.run_dir / "voice.json"
    old = json.loads(voice_path.read_text(encoding="utf-8")) if voice_path.exists() else {}
    entries = {s["index"]: s for s in old.get("scenes", [])}
    only = {int(x) for x in args.only.split(",")} if args.only else None

    print(f"🎙️ 모델 {settings.model} · 속도 {settings.tempo} · 음높이 {settings.pitch}")
    targets = scenes[:1] if args.sample else scenes
    for pos, s in enumerate(targets):
        rel = "voice_sample.wav" if args.sample else f"audio/scene{s.index}.wav"
        out = args.run_dir / rel
        if not args.sample:
            if only is not None and s.index not in only:
                continue
            if only is None and not args.force and out.exists() and s.index in entries \
                    and entries[s.index].get("narration") == s.narration:
                print(f"- 장면 {s.index}: 이미 있음, 건너뜀")
                continue
        prev = scenes[pos - 1].narration if pos > 0 else ""
        nxt = scenes[pos + 1].narration if pos + 1 < len(scenes) else ""
        print(f"- 장면 {s.index} 합성 중 ({len(s.narration)}자)… ", end="", flush=True)
        try:
            speech = typecast.synthesize(settings, s.narration, prev, nxt, **kwargs)
        except typecast.TypecastError as e:
            print("실패")
            sys.exit(f"❌ 장면 {s.index}: {e}")
        out.write_bytes(speech.audio)
        print(f"{speech.duration:.1f}초")
        if not args.sample:
            entries[s.index] = scene_entry(s.index, s.narration, rel, speech)

    if args.sample:
        print(f"✅ 미리 듣기: {args.run_dir / 'voice_sample.wav'}")
        return 0

    ordered = [entries[s.index] for s in scenes if s.index in entries]
    total = sum(e["scene_seconds"] for e in ordered)
    voice = {
        "model": settings.model, "tempo": settings.tempo, "pitch": settings.pitch,
        "lead_in": LEAD_IN, "tail": TAIL,
        "total_seconds": round(total, 2),
        "scenes": ordered,
    }
    voice_path.write_text(json.dumps(voice, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 {voice_path}")

    for e in ordered:
        if e["text_coverage"] < 0.9:
            print(f"⚠️ 장면 {e['index']}: 단어 시각이 내레이션의 {e['text_coverage']:.0%}만 덮습니다. 음성을 들어 보세요.")
    est = timing.estimate_seconds([s.narration for s in scenes])
    print(f"영상 길이 약 {total:.1f}초 (대본 단계 추정 {est:.0f}초)")
    low, high = timing.TARGET_SECONDS
    if total > timing.HARD_MAX_SECONDS:
        print(f"❌ {timing.HARD_MAX_SECONDS}초를 넘습니다. 대본을 줄이세요.")
        return 1
    if not low <= total <= high:
        print(f"⚠️ 목표 {low}~{high}초를 벗어납니다.")
    if len(ordered) < len(scenes):
        print(f"⚠️ 음성이 없는 장면이 {len(scenes) - len(ordered)}개 있습니다.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
