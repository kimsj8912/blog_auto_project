"""Typecast 없이 음성 단계를 돌려 본다(가짜 응답 사용)."""
import base64
import json

import pytest

from shorts.voice import __main__ as cli
from shorts.voice import typecast

from .test_verify import good_storyboard


class FakeResp:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data
        self.text = json.dumps(data)

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, statuses=None):
        self.calls = []
        self.statuses = list(statuses or [])

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(json)
        status = self.statuses.pop(0) if self.statuses else 200
        if status != 200:
            return FakeResp(status, {"message": "nope", "error_code": "X"})
        words = [{"text": w, "start": i * 0.5, "end": i * 0.5 + 0.4}
                 for i, w in enumerate(json["text"].split())]
        return FakeResp(200, {"audio": base64.b64encode(b"RIFFfake").decode(), "words": words,
                              "characters": None, "audio_format": "wav",
                              "audio_duration": 0.5 * len(words)})


@pytest.fixture
def run_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TYPECAST_API_KEY", "test-key")
    monkeypatch.setenv("TYPECAST_VOICE_ID", "tc_test")
    monkeypatch.setenv("TYPECAST_MODEL", "ssfm-v30")
    monkeypatch.setenv("TYPECAST_TEMPO", "0.9")
    monkeypatch.setattr(typecast.time, "sleep", lambda s: None)
    (tmp_path / "storyboard.json").write_text(good_storyboard().model_dump_json(), encoding="utf-8")
    return tmp_path


def test_full_run_writes_audio_and_voice_json(run_dir):
    session = FakeSession()
    assert cli.main(["--run-dir", str(run_dir)], session=session) in (0, 1)

    voice = json.loads((run_dir / "voice.json").read_text(encoding="utf-8"))
    n = len(good_storyboard().scenes)
    assert len(voice["scenes"]) == n and len(session.calls) == n
    first = voice["scenes"][0]
    assert (run_dir / first["file"]).read_bytes() == b"RIFFfake"
    assert first["scene_seconds"] == pytest.approx(0.6 + first["audio_seconds"] + 0.9)
    assert first["text_coverage"] == 1.0
    # 앞뒤 문맥을 넘겨 억양을 잇는다.
    assert session.calls[1]["prompt"]["previous_text"] == good_storyboard().scenes[0].narration
    assert session.calls[0]["output"]["audio_tempo"] == 0.9


def test_second_run_skips_existing_and_only_redoes(run_dir):
    cli.main(["--run-dir", str(run_dir)], session=FakeSession())
    again = FakeSession()
    cli.main(["--run-dir", str(run_dir)], session=again)
    assert again.calls == []
    only = FakeSession()
    cli.main(["--run-dir", str(run_dir), "--only", "2"], session=only)
    assert len(only.calls) == 1


def test_retries_then_succeeds(monkeypatch):
    settings = typecast.Settings(api_key="k", voice_id="v")
    session = FakeSession(statuses=[503, 200])
    monkeypatch.setattr(typecast.time, "sleep", lambda s: None)
    speech = typecast.synthesize(settings, "안녕하세요 반갑습니다", session=session)
    assert len(session.calls) == 2 and len(speech.words) == 2


def test_credit_error_is_explained():
    settings = typecast.Settings(api_key="k", voice_id="v")
    with pytest.raises(typecast.TypecastError, match="크레딧"):
        typecast.synthesize(settings, "안녕", session=FakeSession(statuses=[402]))


def test_text_coverage_detects_skipped_words():
    words = [typecast.Segment("안녕하세요", 0, 1)]
    assert cli.text_coverage("안녕하세요.", words) == 1.0
    assert cli.text_coverage("안녕하세요 오늘은 숏츠를 만듭니다", words) < 0.5


def test_missing_env_exits(tmp_path, monkeypatch):
    monkeypatch.delenv("TYPECAST_API_KEY", raising=False)
    (tmp_path / "storyboard.json").write_text(good_storyboard().model_dump_json(), encoding="utf-8")
    with pytest.raises(SystemExit):
        cli.main(["--run-dir", str(tmp_path)], session=FakeSession())
