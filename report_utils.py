"""Small, dependency-light utilities for report text handling."""
from __future__ import annotations

from collections import Counter
from io import BytesIO
import math
import re

MAX_CHARS = 30_000


def normalize_text(text: str) -> str:
    """Normalize horizontal whitespace while preserving paragraph indentation."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+\n", "\n", text)
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


def chunk_text(text: str, max_words: int = 180, overlap: int = 30) -> list[dict[str, str]]:
    """Split text into overlapping, paragraph-aware chunks with stable source IDs."""
    if max_words < 1 or overlap < 0 or overlap >= max_words:
        raise ValueError("Require max_words >= 1 and 0 <= overlap < max_words.")
    words = normalize_text(text).split()
    chunks = []
    step = max_words - overlap
    for start in range(0, len(words), step):
        part = " ".join(words[start:start + max_words])
        if not part:
            continue
        chunks.append({"id": f"S{len(chunks) + 1}", "text": part})
        if start + max_words >= len(words):
            break
    return chunks


def retrieve_chunks(question: str, chunks: list[dict[str, str]], top_k: int = 4) -> list[dict[str, str]]:
    """Rank report chunks with a lightweight BM25-style lexical relevance score."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")
    tokenize = lambda value: re.findall(r"[a-z0-9_]+", value.lower())
    query_terms = set(tokenize(question))
    if not query_terms or not chunks:
        return []
    tokenized = [tokenize(chunk["text"]) for chunk in chunks]
    avg_len = sum(map(len, tokenized)) / len(tokenized) or 1
    doc_freq = Counter(term for terms in tokenized for term in set(terms))
    scored = []
    for chunk, terms in zip(chunks, tokenized):
        frequencies = Counter(terms)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse = math.log(1 + (len(chunks) - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            denominator = frequency + 1.2 * (1 - 0.75 + 0.75 * len(terms) / avg_len)
            score += inverse * frequency * 2.2 / denominator
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


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
