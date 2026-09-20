import re

from src.config import TEXT_CLEANING_OPTS


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text: collapse runs of whitespace to single space, strip leading/trailing."""
    if not text:
        return text
    return re.sub(r'\s+', ' ', text).strip()


def strip_non_content(text: str) -> str:
    """Remove URLs, email addresses, and phone numbers from text while keeping skill-related content.

    Patterns targeted:
    - HTTP/HTTPS URLs and www. links
    - Email addresses (local@domain.tld)
    - Phone numbers in various formats

    Does NOT strip symbols like ++, ., + that are part of skill tokens (e.g. C++, Node.js, CI/CD).
    """
    if not text:
        return text

    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    text = re.sub(r'\S+@\S+', ' ', text)
    text = re.sub(
        r'(?:\+\d{1,3}\s?)?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}', ' ', text
    )
    text = normalize_whitespace(text)
    return text


def clean_text(raw: str) -> str:
    """Apply TEXT_CLEANING_OPTS toggles to raw resume text.

    Currently supports:
    - remove_urls: strip HTTP/HTTPS URLs and www. links
    - remove_emails: strip email addresses
    - remove_phones: strip phone numbers
    - normalize_whitespace: collapse whitespace runs
    - lowercase: optionally lower case the text (default False to preserve skill cues)

    Returns the cleaned text. Safely handles empty input.
    """
    if not raw:
        return raw

    text = raw
    if TEXT_CLEANING_OPTS.get("remove_urls", False):
        text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    if TEXT_CLEANING_OPTS.get("remove_emails", False):
        text = re.sub(r'\S+@\S+', ' ', text)
    if TEXT_CLEANING_OPTS.get("remove_phones", False):
        text = re.sub(
            r'(?:\+\d{1,3}\s?)?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}', ' ', text
        )
    if TEXT_CLEANING_OPTS.get("normalize_whitespace", False):
        text = normalize_whitespace(text)
    if TEXT_CLEANING_OPTS.get("lowercase", False):
        text = text.lower()
    return text