import pytest
from src.similarity import tfidf_similarity, batch_similarity


def test_tfidf_identical_text_approx_one():
    text = "Python Machine Learning SQL and data analysis with pandas"
    score = tfidf_similarity(text, text)
    assert score == pytest.approx(1.0, abs=0.01)


def test_tfidf_unrelated_text_low_score():
    resume = "Python Machine Learning TensorFlow PyTorch pandas NumPy"
    jd = "Cooking recipe ingredients baking kitchen culinary chef"
    score = tfidf_similarity(resume, jd)
    assert score < 0.3
    assert score >= 0.0


def test_tfidf_empty_string_returns_zero_no_crash():
    assert tfidf_similarity("", "hello world") == 0.0
    assert tfidf_similarity("hello world", "") == 0.0
    assert tfidf_similarity("", "") == 0.0
    assert tfidf_similarity("   ", "hello") == 0.0 or tfidf_similarity("   ", "hello") == pytest.approx(0.0, abs=1e-9)
    # None should also not crash (treated as falsy)
    assert tfidf_similarity(None, "hello") == 0.0
    assert tfidf_similarity("hello", None) == 0.0


def test_batch_similarity_tfidf_identical_and_unrelated():
    jd = "Python SQL data analysis"
    resumes = [
        "Python SQL data analysis",  # identical
        "Cooking baking culinary recipe",  # unrelated
        "Python SQL",  # partial
    ]
    scores = batch_similarity(resumes, jd, method="tfidf")
    assert len(scores) == 3
    assert scores[0] == pytest.approx(1.0, abs=0.01)
    assert scores[1] < 0.3
    # partial should be between
    assert 0.0 < scores[2] < 1.0


def test_batch_similarity_empty_resumes():
    scores = batch_similarity([], "Python SQL", method="tfidf")
    assert scores == []


def test_semantic_similarity_skipped_if_not_installed():
    st = pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed, skipping semantic test")
    from src.similarity import semantic_similarity
    # if we reach here, test basic contract without downloading heavy model if already installed
    # use very small dummy check: empty -> 0.0
    assert semantic_similarity("", "hello") == 0.0
    assert semantic_similarity("hello", "") == 0.0


def test_tfidf_whitespace_only_returns_zero():
    assert tfidf_similarity("   \t\n  ", "Python SQL") == 0.0
