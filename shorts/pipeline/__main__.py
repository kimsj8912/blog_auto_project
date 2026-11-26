"""대본 단계 실행.

    python -m shorts.pipeline --source paper.pdf
    python -m shorts.pipeline --source https://arxiv.org/abs/...
    python -m shorts.pipeline --run-dir .local/runs/<폴더> --from storyboard   # 뒷단계만 다시

결과는 기본으로 .local/runs/ 아래(git 제외)에 저장한다.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from pydantic import BaseModel

from . import report as report_md
from . import stages
from .schemas import Analysis, Perspective, SourceDoc, Storyboard
from .sources import load_source
from .verify import verify

STAGES = ["source", "analysis", "perspective", "storyboard", "verify"]
RUNS_DIR = Path(".local/runs")


def _save(path: Path, model: BaseModel) -> None:
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    print(f"💾 {path}")


def _load(path: Path, schema: type[BaseModel]):
    if not path.exists():
        sys.exit(f"❌ {path}가 없습니다. 앞 단계부터 실행하세요.")
    return schema.model_validate_json(path.read_text(encoding="utf-8"))


def _slug(text: str) -> str:
    text = re.sub(r"[^\w가-힣]+", "-", text).strip("-").lower()
    return text[:40] or "run"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m shorts.pipeline", description="원문 → 스토리보드 JSON")
    p.add_argument("--source", help="PDF·텍스트 파일 경로나 웹 주소")
    p.add_argument("--run-dir", type=Path, help="결과 폴더. 이어서 실행할 때 지정")
    p.add_argument("--from", dest="from_stage", choices=STAGES, default="source",
                   help="이 단계부터 다시 실행(앞 단계 결과는 run-dir에서 읽음)")
    p.add_argument("--perspective", type=Path, help=f"관점 가이드 파일(기본 {stages.DEFAULT_PERSPECTIVE_PATH})")
    args = p.parse_args(argv)

    start = STAGES.index(args.from_stage)
    if start == 0 and not args.source:
        p.error("--source가 필요합니다.")
    if start > 0 and not args.run_dir:
        p.error("--from을 쓰려면 --run-dir가 필요합니다.")

    run_dir = args.run_dir
    files = {
        "source": "source.json", "analysis": "analysis.json", "perspective": "perspective.json",
        "storyboard": "storyboard.json",
    }

    # 1) 원문
    if start <= 0:
        source = load_source(args.source)
        if run_dir is None:
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
            run_dir = RUNS_DIR / f"{stamp}-{_slug(source.title)}"
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"📄 원문: {source.title} ({len(source.text):,}자)")
        _save(run_dir / files["source"], source)
    else:
        source = _load(run_dir / files["source"], SourceDoc)

    # 2) 분석
    if start <= 1:
        print("🔍 분석 중...")
        analysis = stages.analyze(source)
        _save(run_dir / files["analysis"], analysis)
    else:
        analysis = _load(run_dir / files["analysis"], Analysis)

    # 3) 관점 해석
    guide, guide_origin = stages.load_perspective_guide(args.perspective)
    if start <= 2:
        print(f"🧭 관점 해석 중... ({guide_origin})")
        perspective = stages.interpret(analysis, guide)
        _save(run_dir / files["perspective"], perspective)
    else:
        perspective = _load(run_dir / files["perspective"], Perspective)

    # 4) 스토리보드
    if start <= 3:
        print("🎬 스토리보드 작성 중...")
        storyboard = stages.write_storyboard(analysis, perspective)
        _save(run_dir / files["storyboard"], storyboard)
    else:
        storyboard = _load(run_dir / files["storyboard"], Storyboard)

    # 5) 원문 대조 검사와 검수 보고서
    result = verify(source.text, analysis, perspective, storyboard)
    (run_dir / "verify.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    md = report_md.render(source, analysis, perspective, storyboard, result, guide_origin)
    (run_dir / "review.md").write_text(md, encoding="utf-8")
    print(f"📝 {run_dir / 'review.md'}")

    counts = {lv: sum(i.level == lv for i in result.issues) for lv in ("error", "warning", "check")}
    print(f"예상 길이 약 {result.estimated_seconds:.0f}초 · 오류 {counts['error']} · "
          f"경고 {counts['warning']} · 사람 확인 {counts['check']}")
    if not result.ok:
        print("❌ 오류가 있어 다음 단계로 넘기면 안 됩니다. review.md를 보고 고친 뒤 "
              f"--run-dir {run_dir} --from storyboard 로 다시 실행하세요.")
        return 1
    print("✅ 기계 검사 통과. review.md로 사람 검수 후 승인하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
