from report_utils import chunk_text, local_outline, normalize_text, retrieve_chunks, validate_text


def test_normalize_text_collapses_whitespace_but_keeps_paragraphs():
    assert normalize_text("  hello\tworld \n\n\n next ") == "hello world\n\n next"


def test_validate_text_rejects_empty_input():
    ok, message = validate_text("  ")
    assert not ok
    assert "provide report text" in message.lower()


def test_validate_text_rejects_text_over_limit():
    ok, message = validate_text("abcd", max_chars=3)
    assert not ok
    assert "too long" in message.lower()


def test_validate_text_accepts_valid_input():
    assert validate_text("A short report.") == (True, "OK")


def test_local_outline_is_explicit_about_heuristics():
    result = local_outline("This is the first sentence. This is the second.\n\nA finding is described here.")
    assert "not an AI-generated interpretation" in result
    assert "Review questions" in result


def test_chunk_text_creates_overlapping_source_passages():
    chunks = chunk_text(" ".join(f"word{i}" for i in range(20)), max_words=10, overlap=2)
    assert [chunk["id"] for chunk in chunks] == ["S1", "S2", "S3"]
    assert chunks[0]["text"].split()[-2:] == chunks[1]["text"].split()[:2]


def test_retrieve_chunks_ranks_relevant_passage_first():
    chunks = [
        {"id": "S1", "text": "Revenue increased by twelve percent during the quarter."},
        {"id": "S2", "text": "The hiring plan adds five engineering roles next year."},
        {"id": "S3", "text": "Customer churn declined after the pricing change."},
    ]
    results = retrieve_chunks("What happened to revenue growth?", chunks)
    assert results
    assert results[0]["id"] == "S1"


def test_retrieve_chunks_returns_empty_for_no_overlap():
    chunks = [{"id": "S1", "text": "The report discusses revenue and sales."}]
    assert retrieve_chunks("volcanic activity", chunks) == []
