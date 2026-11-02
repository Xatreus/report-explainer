from report_utils import local_outline, normalize_text, validate_text


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
