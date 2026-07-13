"""Extract raw text from the input file (PDF or plain text)."""

from pathlib import Path


def extract_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if p.suffix.lower() == ".pdf":
        return _extract_pdf(p)
    return p.read_text(encoding="utf-8", errors="replace")


def _extract_pdf(p: Path) -> str:
    import pdfplumber

    pages = []
    with pdfplumber.open(p) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError(
            f"No selectable text found in {p.name}. "
            "If this is a scanned PDF, run OCR on it first (e.g. with ocrmypdf)."
        )
    return text
