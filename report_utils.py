"""Small, dependency-light utilities for report text handling."""
from __future__ import annotations

from io import BytesIO
import re

MAX_CHARS = 30_000


def normalize_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph boundaries."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def validate_text(text: str, max_chars: int = MAX_CHARS) -> tuple[bool, str]:
    """Return whether text is non-empty and within the configured size limit."""
    if not text.strip():
        return False, "Please provide report text or upload a text-based PDF."
    if len(text) > max_chars:
        return False, f"Report text is too long ({len(text):,} characters). The limit is {max_chars:,} characters."
    return True, "OK"


def extract_pdf_text(data: bytes) -> str:
    """Extract selectable text from a PDF byte stream."""
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    return normalize_text("\n\n".join(page.extract_text() or "" for page in reader.pages))


def local_outline(text: str) -> str:
    """Build a transparent, non-generative outline without calling an AI service."""
    text = normalize_text(text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    key_lines = [p.replace("\n", " ") for p in paragraphs[:5]]
    summary = " ".join(sentences[:3]) or text[:500]
    return (
        "# Report outline (local mode)\n\n"
        "> This is a heuristic outline, not an AI-generated interpretation. Verify details against the source.\n\n"
        "## Opening summary\n\n" + summary[:1800] + "\n\n"
        "## Early sections / key paragraphs\n\n"
        + ("\n".join(f"- {line[:500]}" for line in key_lines) if key_lines else "- No paragraphs detected.")
        + "\n\n## Review questions\n\n"
        "- What is the report's main conclusion?\n"
        "- Which figures or claims are supported by evidence?\n"
        "- What assumptions, risks, or limitations are mentioned?\n"
        "- What information is missing before acting on the findings?\n"
    )
