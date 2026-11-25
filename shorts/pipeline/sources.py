"""원문 읽기: PDF 파일, 텍스트·마크다운 파일, 웹 주소(HTML·PDF)를 본문 텍스트로 바꾼다."""
import io
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .schemas import SourceDoc

# Gemini Flash 문맥 창은 충분히 크지만, 비용과 응답 품질을 위해 너무 긴 원문은 자른다.
MAX_CHARS = 400_000

USER_AGENT = "Mozilla/5.0 (compatible; shorts-pipeline/0.1)"


def load_source(source: str) -> SourceDoc:
    if re.match(r"https?://", source):
        doc = _load_url(source)
    else:
        doc = _load_file(Path(source))
    if len(doc.text) > MAX_CHARS:
        print(f"⚠️ 원문이 {len(doc.text):,}자라 앞 {MAX_CHARS:,}자만 씁니다.")
        doc.text = doc.text[:MAX_CHARS]
    if not doc.text.strip():
        raise ValueError(f"원문에서 텍스트를 찾지 못했습니다: {source}")
    return doc


def _load_file(path: Path) -> SourceDoc:
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        title, text = _pdf_text(path.read_bytes())
    elif suffix in (".html", ".htm"):
        title, text = _html_text(path.read_text(encoding="utf-8"))
    else:
        text = path.read_text(encoding="utf-8")
        title = _first_line(text)
    return SourceDoc(origin=str(path), title=title or path.stem, text=text)


def _load_url(url: str) -> SourceDoc:
    # arXiv 초록 페이지는 본문이 없으므로 PDF로 바꿔 받는다.
    m = re.match(r"https?://arxiv\.org/abs/([^?#]+)", url)
    fetch_url = f"https://arxiv.org/pdf/{m.group(1)}" if m else url

    resp = requests.get(fetch_url, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    if "pdf" in content_type or resp.content[:5] == b"%PDF-":
        title, text = _pdf_text(resp.content)
    else:
        title, text = _html_text(resp.text)
    return SourceDoc(origin=url, title=title or url, text=text)


def _pdf_text(data: bytes) -> tuple[str, str]:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages)
    title = (reader.metadata.title if reader.metadata else None) or _first_line(text)
    return title, text


def _html_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    body = soup.find("article") or soup.find("main") or soup.body or soup
    lines = [line.strip() for line in body.get_text("\n").splitlines()]
    text = "\n".join(line for line in lines if line)
    return title, text


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip().lstrip("# ")[:200]
    return ""
