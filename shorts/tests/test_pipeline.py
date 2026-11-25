"""Gemini 없이 파이프라인 전체를 돌려 본다(가짜 응답 사용)."""
import json
from pathlib import Path

import gemini_client
from shorts.pipeline import __main__ as cli
from shorts.pipeline import sources
from shorts.pipeline.schemas import Analysis, Perspective, Storyboard

from .test_verify import good_storyboard, make_analysis, make_perspective

FIXTURE = Path(__file__).parent / "fixtures" / "sample_source.txt"


def fake_generate_json(responses):
    calls = []

    def _fake(prompt, schema, system=None):
        calls.append((schema, prompt, system))
        return responses[schema]

    return _fake, calls


def test_full_run_writes_outputs(tmp_path, monkeypatch):
    fake, calls = fake_generate_json({
        Analysis: make_analysis(), Perspective: make_perspective(), Storyboard: good_storyboard(),
    })
    monkeypatch.setattr(gemini_client, "generate_json", fake)
    run_dir = tmp_path / "run"

    code = cli.main(["--source", str(FIXTURE), "--run-dir", str(run_dir),
                     "--perspective", str(tmp_path / "없는파일.md")])

    assert code == 0
    assert [c[0] for c in calls] == [Analysis, Perspective, Storyboard]
    # 관점 가이드가 없으면 중립 해설 문구가 들어간다.
    assert "특정 회사·브랜드 관점 없이" in calls[1][2]
    for name in ["source.json", "analysis.json", "perspective.json", "storyboard.json",
                 "verify.json", "review.md"]:
        assert (run_dir / name).exists(), name
    assert json.loads((run_dir / "verify.json").read_text(encoding="utf-8"))["ok"] is True
    review = (run_dir / "review.md").read_text(encoding="utf-8")
    assert "검사 통과" in review and "coordinators earn 2.41" in review


def test_rerun_from_storyboard_reuses_earlier_stages(tmp_path, monkeypatch):
    bad = good_storyboard()
    bad.scenes[2].narration = "조정자는 2.41을 받습니다."
    fake, calls = fake_generate_json({
        Analysis: make_analysis(), Perspective: make_perspective(), Storyboard: bad,
    })
    monkeypatch.setattr(gemini_client, "generate_json", fake)
    run_dir = tmp_path / "run"
    assert cli.main(["--source", str(FIXTURE), "--run-dir", str(run_dir)]) == 1

    fake2, calls2 = fake_generate_json({Storyboard: good_storyboard()})
    monkeypatch.setattr(gemini_client, "generate_json", fake2)
    assert cli.main(["--run-dir", str(run_dir), "--from", "storyboard"]) == 0
    assert [c[0] for c in calls2] == [Storyboard]


def test_perspective_guide_from_local_file(tmp_path):
    guide = tmp_path / "perspective.md"
    guide.write_text("테스트 관점", encoding="utf-8")
    from shorts.pipeline.stages import load_perspective_guide
    assert load_perspective_guide(guide) == ("테스트 관점", str(guide))


def test_load_html_file_drops_nav_and_scripts(tmp_path):
    page = tmp_path / "a.html"
    page.write_text(
        "<html><head><title>기사 제목</title><script>x=1</script></head><body>"
        "<nav>메뉴</nav><article><p>본문 첫 줄</p><p>둘째 줄</p></article><footer>꼬리</footer>"
        "</body></html>", encoding="utf-8")
    doc = sources.load_source(str(page))
    assert doc.title == "기사 제목"
    assert doc.text == "본문 첫 줄\n둘째 줄"


def test_load_text_file_uses_first_line_as_title():
    doc = sources.load_source(str(FIXTURE))
    assert doc.title.startswith("Coordination Premiums")


def test_arxiv_abs_url_is_fetched_as_pdf(monkeypatch):
    seen = {}

    class Resp:
        headers = {"content-type": "text/html"}
        content = b"<html><body><main>paper body</main></body></html>"
        text = content.decode()

        def raise_for_status(self):
            pass

    def fake_get(url, **kw):
        seen["url"] = url
        return Resp()

    monkeypatch.setattr(sources.requests, "get", fake_get)
    sources.load_source("https://arxiv.org/abs/2611.05417")
    assert seen["url"] == "https://arxiv.org/pdf/2611.05417"


def test_schemas_convert_for_gemini():
    """SDK가 스키마를 Gemini 형식으로 바꿀 수 있는지(네트워크 없이)."""
    from google.genai import types
    for schema in (Analysis, Perspective, Storyboard):
        config = types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema)
        assert config.response_schema is schema
