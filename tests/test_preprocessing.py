import pytest
from src.preprocessing import clean_text, normalize_whitespace, strip_non_content


# --- empty / None / whitespace edge cases ---

def test_clean_text_empty_string_returns_empty():
    result = clean_text("")
    assert result == ""


def test_clean_text_whitespace_only_returns_empty():
    assert clean_text("   ") == ""
    assert clean_text("\t\n  \n\t") == ""
    assert clean_text("  \t  ") == ""


def test_clean_text_none_does_not_crash():
    # implementation returns None for None input (falsy guard); accept None or ""
    result = clean_text(None)
    assert result is None or result == ""


def test_normalize_whitespace_empty_and_none():
    assert normalize_whitespace("") == ""
    assert normalize_whitespace(None) is None or normalize_whitespace(None) == ""


def test_normalize_whitespace_collapses_spaces():
    assert normalize_whitespace("  hello   world \t\n foo  ") == "hello world foo"


def test_strip_non_content_none_and_empty():
    assert strip_non_content("") == ""
    # should not raise on None
    result = strip_non_content(None)
    assert result is None or result == ""


# --- skill-token preservation ---

def test_clean_text_preserves_cpp():
    text = "Experienced in C++ and Python"
    cleaned = clean_text(text)
    assert "C++" in cleaned


def test_clean_text_preserves_nodejs():
    text = "Built APIs with Node.js and React"
    cleaned = clean_text(text)
    assert "Node.js" in cleaned


def test_clean_text_preserves_cicd():
    text = "CI/CD pipeline with Docker and Jenkins"
    cleaned = clean_text(text)
    assert "CI/CD" in cleaned


def test_clean_text_preserves_all_three_together():
    text = "C++ Node.js CI/CD"
    cleaned = clean_text(text)
    assert "C++" in cleaned
    assert "Node.js" in cleaned
    assert "CI/CD" in cleaned


# --- PII / URL stripping ---

def test_clean_text_strips_urls():
    text = "Portfolio https://example.com and www.test.org and http://foo.bar/baz"
    cleaned = clean_text(text)
    assert "https://example.com" not in cleaned
    assert "www.test.org" not in cleaned
    assert "http://foo.bar/baz" not in cleaned
    # surrounding words should remain
    assert "Portfolio" in cleaned


def test_clean_text_strips_emails():
    text = "Contact me at test@example.com or foo.bar@company.co.uk for details"
    cleaned = clean_text(text)
    assert "test@example.com" not in cleaned
    assert "foo.bar@company.co.uk" not in cleaned
    assert "Contact" in cleaned


def test_clean_text_strips_phones():
    # various phone formats
    for phone in ["123-456-7890", "123 456 7890", "(123) 456-7890", "+1 (123) 456-7890"]:
        text = f"Call me at {phone} tomorrow"
        cleaned = clean_text(text)
        # digits fragments should be removed, not crash
        assert phone not in cleaned
        assert "Call" in cleaned


def test_strip_non_content_strips_all_pii_inline():
    text = "Email test@example.com visit https://example.com call 123-456-7890"
    result = strip_non_content(text)
    assert "test@example.com" not in result
    assert "https://example.com" not in result
    assert "123-456-7890" not in result


# --- Unicode preservation ---

def test_clean_text_preserves_unicode_e_acute():
    text = "r\u00e9sum\u00e9 and caf\u00e9"
    cleaned = clean_text(text)
    assert "r\u00e9sum\u00e9" in cleaned
    assert "caf\u00e9" in cleaned


def test_clean_text_preserves_chinese_characters():
    text = "\u4f60\u597d world test"
    cleaned = clean_text(text)
    assert "\u4f60\u597d" in cleaned


def test_clean_text_preserves_mixed_unicode_and_pii():
    text = "caf\u00e9 \u4f60\u597d contact test@example.com https://example.com"
    cleaned = clean_text(text)
    assert "caf\u00e9" in cleaned
    assert "\u4f60\u597d" in cleaned
    assert "test@example.com" not in cleaned
    assert "https://example.com" not in cleaned
