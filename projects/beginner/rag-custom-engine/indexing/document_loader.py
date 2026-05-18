"""
Multi-format document loader — no LangChain.
Supports PDF, TXT, DOCX, CSV, Markdown.
Returns a list of dicts: {"content": str, "metadata": {source, page}}.
"""

import csv
import io
from pathlib import Path


def load_document(file_path: str) -> list[dict]:
    path = Path(file_path)
    ext = path.suffix.lower()

    loaders = {
        ".pdf": _load_pdf,
        ".txt": _load_text,
        ".md": _load_text,
        ".docx": _load_docx,
        ".csv": _load_csv,
    }

    loader = loaders.get(ext)
    if loader is None:
        raise ValueError(f"Unsupported file type: {ext}")

    docs = loader(path)
    filename = path.name
    for doc in docs:
        doc["metadata"]["source_filename"] = filename

    return docs


def _load_pdf(path: Path) -> list[dict]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    docs = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            docs.append({"content": text, "metadata": {"page": i + 1}})
    return docs


def _load_text(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []
    return [{"content": text, "metadata": {"page": 1}}]


def _load_docx(path: Path) -> list[dict]:
    from docx import Document as DocxDocument

    doc = DocxDocument(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        return []
    full_text = "\n\n".join(paragraphs)
    return [{"content": full_text, "metadata": {"page": 1}}]


def _load_csv(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    header = rows[0]
    lines = []
    for row in rows[1:]:
        pairs = [f"{h}: {v}" for h, v in zip(header, row) if v.strip()]
        if pairs:
            lines.append("; ".join(pairs))
    if not lines:
        return []
    return [{"content": "\n".join(lines), "metadata": {"page": 1}}]
