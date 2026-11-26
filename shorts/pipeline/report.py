"""검수용 보고서(마크다운). 스토리보드 승인자가 원문 근거와 같이 읽는다."""
from .schemas import Analysis, Perspective, SourceDoc, Storyboard
from .verify import Report

_LEVEL_LABEL = {"error": "오류", "warning": "경고", "check": "사람 확인"}


def render(source: SourceDoc, analysis: Analysis, perspective: Perspective,
           storyboard: Storyboard, report: Report, perspective_origin: str) -> str:
    claims = {c.id: c for c in analysis.claims}
    numbers = {n.id: n for n in analysis.numbers}
    interps = {i.id: i for i in perspective.interpretations}

    status = "검사 통과, 사람 검수 대기" if report.ok else f"오류 {len(report.errors)}건, 수정 필요"
    out = [
        f"# 스토리보드 검수: {storyboard.title}",
        "",
        f"- 원문: {source.title} ({source.origin})",
        f"- 관점: {perspective_origin}",
        f"- 예상 길이: 약 {report.estimated_seconds:.0f}초, 장면 {len(storyboard.scenes)}개",
        f"- 상태: **{status}**",
        "",
        "> 기계 검사는 인용·숫자·표기·길이·해석 표시만 봅니다. 의미가 원문과 같은지는 사람이 확인해야 합니다.",
        "",
    ]

    if report.issues:
        out += ["## 검사 결과", "", "| 수준 | 위치 | 내용 |", "|---|---|---|"]
        order = {"error": 0, "warning": 1, "check": 2}
        for i in sorted(report.issues, key=lambda i: order[i.level]):
            out.append(f"| {_LEVEL_LABEL[i.level]} | {i.where} | {_cell(i.message)} |")
        out.append("")

    out += ["## 장면", ""]
    for s in storyboard.scenes:
        out += [f"### {s.index}. {s.purpose}", "", f"**내레이션** {s.narration}", ""]
        if s.on_screen_text:
            out.append("**화면**")
            out += [f"- {line}" for line in s.on_screen_text]
            out.append("")
        out += [f"**연출** {s.visual_intent}", ""]
        for cid in s.claim_ids:
            if c := claims.get(cid):
                out.append(f"- 근거 {cid}: {c.statement}")
                out.append(f"  > {c.quote}")
        for sn in s.numbers:
            src = numbers.get(sn.source_number_id)
            if src:
                note = f" · 설정: {src.setting}" if src.setting else ""
                tag = " · 예시값" if src.is_illustrative or sn.is_illustrative else ""
                out.append(f"- 숫자 {sn.display} ← {src.id} {src.value}: {src.meaning}{note}{tag}")
                out.append(f"  > {src.quote}")
            else:
                out.append(f"- 숫자 {sn.display}: 원문 출처 없음{' (예시값)' if sn.is_illustrative else ''}")
        for iid in s.interpretation_ids:
            if i := interps.get(iid):
                out.append(f"- 우리 해석 {iid}: {i.text} (근거 {', '.join(i.based_on)})")
        out.append("")

    if analysis.caveats:
        out += ["## 원문이 밝힌 한계·오해하기 쉬운 지점", ""]
        out += [f"- {c}" for c in analysis.caveats]
        out.append("")
    return "\n".join(out)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")
