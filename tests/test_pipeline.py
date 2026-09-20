import json
import pytest
from pathlib import Path

from src.pipeline import build_candidate_result, generate_explanation, screen_resumes
from src.job_parser import JobProfile

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_JOBS = ROOT / "data" / "raw" / "sample_jobs.json"

# --- original self-checks preserved ---

def test_generate_explanation_perfect_match_high_similarity():
    result_a = generate_explanation({
        "matched_skills": ["Python", "SQL"],
        "missing_skills": [],
        "additional_skills": [],
        "similarity": 0.9,
    })
    assert "Strong required-skill coverage" in result_a
    assert "High similarity to job description" in result_a

def test_generate_explanation_zero_match_low_similarity():
    result_b = generate_explanation({
        "matched_skills": [],
        "missing_skills": ["Python", "SQL"],
        "additional_skills": [],
        "similarity": 0.1,
    })
    assert "Missing: Python, SQL" in result_b or "Insufficient" in result_b or "Missing" in result_b

def test_generate_explanation_partial_moderate():
    result_c = generate_explanation({
        "matched_skills": ["Python"],
        "missing_skills": ["SQL"],
        "additional_skills": [],
        "similarity": 0.5,
    })
    assert "Moderate similarity to job description" in result_c
    assert "Missing: SQL" in result_c

def test_generate_explanation_determinism():
    payload = {
        "matched_skills": ["Python"],
        "missing_skills": ["SQL"],
        "additional_skills": [],
        "similarity": 0.5,
    }
    assert generate_explanation(payload) == generate_explanation(payload)

def test_generate_explanation_no_signal_fallback():
    result_e = generate_explanation({
        "matched_skills": [],
        "missing_skills": [],
        "additional_skills": [],
        "similarity": 0.1,
    })
    assert "Insufficient signal to explain ranking" in result_e

# --- Phase 11 required additions ---

def _fixture_job():
    # Prefer sample_jobs.json if present, else synthetic fallback
    if SAMPLE_JOBS.exists():
        try:
            with open(SAMPLE_JOBS, "r", encoding="utf-8") as f:
                jobs = json.load(f)
            if jobs:
                # pick first job with required_skills or first overall
                for j in jobs:
                    if j.get("required_skills"):
                        return j
                return jobs[0]
        except Exception:
            pass
    # synthetic fallback
    return {
        "role": "Machine Learning Engineer",
        "description": "Python SQL Machine Learning Docker AWS",
        "required_skills": ["Python", "SQL"],
        "optional_skills": ["AWS"],
    }

def test_screen_resumes_returns_three_results():
    job = _fixture_job()
    # use synthetic resumes to avoid PDF dependency
    resumes = [
        {"candidate_id": "c1", "text": "Python SQL Machine Learning expertise with AWS"},
        {"candidate_id": "c2", "text": "Python SQL experience"},
        {"candidate_id": "c3", "text": "cooking recipe culinary baking"},
    ]
    results = screen_resumes(job, resumes)
    assert len(results) == 3
    assert isinstance(results, list)

def test_screen_resumes_each_result_has_exactly_8_keys():
    job = _fixture_job()
    resumes = [
        {"candidate_id": "c1", "text": "Python SQL"},
        {"candidate_id": "c2", "text": "Java cooking"},
        {"candidate_id": "c3", "text": "Python AWS"},
    ]
    results = screen_resumes(job, resumes)
    expected_keys = {"rank", "candidate_id", "overall_score", "matched_skills", "missing_skills", "similarity", "score_breakdown", "explanation"}
    for r in results:
        assert set(r.keys()) == expected_keys, f"got {set(r.keys())} expected {expected_keys}"
        assert len(r.keys()) == 8

def test_screen_resumes_determinism_identical_ordering():
    job = _fixture_job()
    resumes = [
        {"candidate_id": "c1", "text": "Python SQL Machine Learning"},
        {"candidate_id": "c2", "text": "Python SQL"},
        {"candidate_id": "c3", "text": "cooking recipe"},
    ]
    first = screen_resumes(job, resumes)
    second = screen_resumes(job, resumes)
    assert first == second
    # ordering should be deterministic by (-final_score, candidate_id)
    assert [r["candidate_id"] for r in first] == [r["candidate_id"] for r in second]

def test_screen_resumes_empty_list_returns_empty():
    job = _fixture_job()
    assert screen_resumes(job, []) == []
    assert screen_resumes(job, [], weights={"beta": 0.5}) == []

def test_screen_resumes_with_sample_jobs_skip_gracefully():
    if not SAMPLE_JOBS.exists():
        pytest.skip("sample_jobs.json missing, skipping")
    with open(SAMPLE_JOBS, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    if not jobs:
        pytest.skip("sample_jobs.json empty")
    job = jobs[0]
    resumes = [
        {"candidate_id": "r1", "text": "Python SQL Docker"},
        {"candidate_id": "r2", "text": "Machine Learning Python"},
        {"candidate_id": "r3", "text": "cooking"},
    ]
    results = screen_resumes(job, resumes)
    assert len(results) == 3
    for r in results:
        assert "explanation" in r

def test_build_candidate_result_has_expected_structure():
    from src.scoring import score_candidate
    job = JobProfile(role="Test", clean_description="Python SQL", required_skills=["Python", "SQL"], optional_skills=[], raw_text="Python SQL")
    resume = {"candidate_id": "c1", "text": "Python SQL"}
    from src.similarity import tfidf_similarity
    sim = tfidf_similarity("Python SQL", "Python SQL")
    score_dict = score_candidate(resume, job, sim)
    result = build_candidate_result("c1", job, sim, score_dict)
    # build_candidate_result returns 7 keys (without rank), screen_resumes wraps to 8
    assert "candidate_id" in result
    assert "overall_score" in result
    assert "score_breakdown" in result
