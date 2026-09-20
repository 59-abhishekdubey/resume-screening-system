# src/similarity.py
# TF-IDF and semantic similarity functions for resume-to-JD comparison.
# - tfidf_similarity: fits vectorizer on [resume, JD] jointly per call (fine for
#   pairwise; for batch ranking, fit once on the full corpus externally).
# - semantic_similarity: lazy-loads SentenceTransformer at module level; import cost
#   is only paid when this function is first called.
# - batch_similarity: dispatches to the chosen method for multiple resumes vs one JD.

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

_semantic_model = None
_model_name: str | None = None


def _get_semantic_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    global _semantic_model, _model_name
    if _semantic_model is None or _model_name != model_name:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _semantic_model = SentenceTransformer(model_name)
        _model_name = model_name
    return _semantic_model


def tfidf_similarity(resume_text: str, jd_text: str) -> float:
    """Compute TF-IDF cosine similarity between resume and job description.

    For pairwise similarity the vectorizer is fit on [resume_text, jd_text] jointly
    each call. This is acceptable for a single pair but would be a data leak if the
    vectorizer were fitted on a training corpus and then reused for new resumes/JDs.
    For batch ranking, fit TfidfVectorizer once on the full corpus before calling.

    Returns 0.0 if either text is empty.
    """
    if not resume_text or not jd_text:
        return 0.0

    vectorizer = TfidfVectorizer()
    # Fit jointly on both texts for pairwise comparison
    vectors = vectorizer.fit_transform([resume_text, jd_text])
    a = vectors[0].toarray().ravel()
    b = vectors[1].toarray().ravel()
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def semantic_similarity(
    resume_text: str,
    jd_text: str,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> float:
    """Compute semantic (sentence-transformer) cosine similarity.

    Lazily loads the SentenceTransformer model at module level the first time it is
    called, so the import/download cost is not paid unless similarity is actually used.
    The model is cached at the module level for subsequent calls.

    Returns 0.0 if either text is empty.
    """
    if not resume_text or not jd_text:
        return 0.0

    model = _get_semantic_model(model_name)
    embeddings = model.encode([resume_text, jd_text], normalize_embeddings=True)
    return float(np.dot(embeddings[0], embeddings[1]))  # already cosine with norm=1


def batch_similarity(
    resumes: list[str], jd: str, method: str = "tfidf"
) -> list[float]:
    """Compute similarity for multiple resumes against a single job description.

    Parameters
    ----------
    resumes : list[str]
        List of resume text strings.
    jd : str
        Job description text.
    method : {"tfidf", "semantic"}
        Similarity method to use.

    Returns
    -------
    list[float]
        Similarity scores in the same order as the input resumes.
    """
    method = method.lower()
    if method == "tfidf":
        return [tfidf_similarity(r, jd) for r in resumes]
    if method == "semantic":
        return [semantic_similarity(r, jd) for r in resumes]
    raise ValueError(f'Unknown method "{method}"; use "tfidf" or "semantic"')