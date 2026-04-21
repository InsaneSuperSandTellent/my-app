from pathlib import Path

import pdfplumber


def extract_text(filepath: Path) -> str | None:
    try:
        with pdfplumber.open(filepath) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as exc:
        return f"ERROR: {exc}"

    stripped = text.strip()
    return stripped if stripped else None
