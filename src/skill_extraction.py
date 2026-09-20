import re

from src.config import SKILL_VOCABULARY, SKILL_ALIASES


def extract_skills(clean_text: str) -> list[str]:
    """Extract canonical skill names from clean text.

    Uses word-boundary regex matching and alias lookup to find skills.
    Returns canonical skill names in order of appearance, deduplicated.

    - Word boundaries (\b) prevent false positives (e.g. "R" does not match
      inside "React").
    - Multi-word skills ("Machine Learning") are handled via phrase regex.
    - Aliases (e.g. "sklearn" → "Scikit-learn") are resolved to canonical names.
    """
    if not clean_text or not clean_text.strip():
        return []

    # Collect (position, canonical_skill) matches
    matches: list[tuple[int, str]] = []

    # 1. Token-based alias matching: split by whitespace, strip surrounding
    #    punctuation, check lowercased token against SKILL_ALIASES
    tokens = clean_text.split()
    for idx, token in enumerate(tokens):
        stripped = token.strip('.,;:!?\'"()[]')
        lower_stripped = stripped.lower()
        if lower_stripped in SKILL_ALIASES:
            canonical = SKILL_ALIASES[lower_stripped]
            matches.append((idx, canonical))

    # 2. Direct regex matching for canonical skill names with word boundaries
    #    This catches cases where the canonical name appears without going
    #    through the alias map (e.g. "Scikit-learn" vs "sklearn")
    for skill in SKILL_VOCABULARY:
        pattern = r'(?i)\b' + re.escape(skill) + r'\b'
        for m in re.finditer(pattern, clean_text):
            # Direct regex match (may overlap with alias matching; deduplication
    # happens below via the seen set)
            span = m.span()
            matches.append((span[0], skill))

    # Sort by position of first appearance (idx for tokens, char pos for regex)
    matches.sort(key=lambda x: (x[0], x[1]))

    # Deduplicate while preserving order
    result: list[str] = []
    seen: set[str] = set()
    for _pos, skill in matches:
        if skill not in seen:
            seen.add(skill)
            result.append(skill)

    return result


def match_by_alias(text: str) -> set[str]:
    """Lower-level helper: find canonical skill names by checking tokens against
    SKILL_ALIASES. Returns a set (order not guaranteed)."""
    if not text or not text.strip():
        return set()

    found: set[str] = set()
    tokens = text.split()
    for token in tokens:
        stripped = token.strip('.,;:!?\'"()[]')
        lower_stripped = stripped.lower()
        if lower_stripped in SKILL_ALIASES:
            found.add(SKILL_ALIASES[lower_stripped])
    return found


def explain_match(skill: str, text: str) -> str:
    """Return the surface substring in *text* that triggered the match for *skill*.

    Uses word-boundary regex (\b) so that e.g. explain_match("R", "I love React")
    returns None (no false positive inside "React").
    If no match is found, returns None."""
    if not skill or not text:
        return None

    pattern = r'(?i)\b' + re.escape(skill) + r'\b'
    m = re.search(pattern, text)
    if m:
        return m.group(0)
    return None