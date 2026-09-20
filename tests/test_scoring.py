import pytest
from src.scoring import score_candidate, WEIGHTS
from src.job_parser import JobProfile


def _make_job(required=None, optional=None, description=""):
    return JobProfile(
        role="Test",
        clean_description=description,
        required_skills=required or [],
        optional_skills=optional or [],
        raw_text=description,
    )


def test_perfect_skill_match_outranks_zero_match():
    job = _make_job(required=["Python", "SQL"], optional=["AWS"], description="Python SQL")
    perfect = {"text": "Python and SQL expertise with AWS", "candidate_id": "perfect"}
    zero = {"text": "cooking baking culinary recipe", "candidate_id": "zero"}
    # same similarity to isolate skill effect
    sim = 0.8
    score_perfect = score_candidate(perfect, job, sim)
    score_zero = score_candidate(zero, job, sim)
    assert score_perfect["final_score"] > score_zero["final_score"]
    assert score_perfect["skill_component"] > score_zero["skill_component"]


def test_weight_changes_shift_ranking_predictably():
    job = _make_job(required=["Python", "SQL"], optional=["Docker", "AWS"], description="Python SQL Docker")
    # candidate A: only required, no optional
    cand_a = {"text": "Python SQL", "candidate_id": "a"}
    # candidate B: required + all optional
    cand_b = {"text": "Python SQL Docker AWS", "candidate_id": "b"}
    sim = 0.8
    # low beta -> optional matters little, both close
    low_beta = score_candidate(cand_a, job, sim, weights={"beta": 0.1})
    low_beta_b = score_candidate(cand_b, job, sim, weights={"beta": 0.1})
    # high beta -> optional matters more, candidate without optional penalized
    high_beta = score_candidate(cand_a, job, sim, weights={"beta": 2.0})
    high_beta_b = score_candidate(cand_b, job, sim, weights={"beta": 2.0})
    # with high beta, skill_component for cand_a should drop compared to low beta
    assert high_beta["skill_component"] < low_beta["skill_component"]
    # candidate B has all optional, so its skill_component stays 1.0 regardless
    assert low_beta_b["skill_component"] == pytest.approx(1.0)
    assert high_beta_b["skill_component"] == pytest.approx(1.0)
    # gap between A and B widens with higher beta
    gap_low = low_beta_b["final_score"] - low_beta["final_score"]
    gap_high = high_beta_b["final_score"] - high_beta["final_score"]
    assert gap_high > gap_low


def test_empty_required_skills_does_not_crash():
    job = _make_job(required=[], optional=[], description="")
    cand = {"text": "Python SQL", "candidate_id": "c1"}
    result = score_candidate(cand, job, 0.5)
    # should not crash, final_score defined
    assert "final_score" in result
    assert result["total_required"] == 0
    # empty required also with empty resume
    result2 = score_candidate({"text": ""}, job, 0.5)
    assert result2["final_score"] >= 0.0

def test_empty_required_with_optional_only():
    job = _make_job(required=[], optional=["Python", "SQL"], description="Python SQL")
    cand = {"text": "Python SQL", "candidate_id": "c1"}
    result = score_candidate(cand, job, 0.7)
    # job_profile branch with tr_total==0 returns skill_component 1.0 per scoring.py
    assert result["skill_component"] == 1.0
    assert result["final_score"] == pytest.approx(0.7)


def test_score_breakdown_has_all_9_keys():
    job = _make_job(required=["Python"], optional=["AWS"], description="Python")
    cand = {"text": "Python AWS", "candidate_id": "c1"}
    result = score_candidate(cand, job, 0.6)
    expected_keys = {
        "matched_required",
        "missing_required",
        "matched_additional",
        "total_required",
        "total_additional",
        "beta",
        "skill_component",
        "similarity_component",
        "final_score",
    }
    assert set(result.keys()) == expected_keys
    # also verify types
    assert isinstance(result["matched_required"], list)
    assert isinstance(result["total_required"], int)
    assert isinstance(result["beta"], float) or isinstance(result["beta"], int)
    assert 0.0 <= result["skill_component"] <= 1.0
    assert 0.0 <= result["final_score"] <= 1.0


def test_score_dict_job_as_dict_not_only_dataclass():
    job_dict = {"required_skills": ["Python"], "optional_skills": ["AWS"]}
    cand = {"text": "Python", "candidate_id": "c1"}
    result = score_candidate(cand, job_dict, 0.5)
    assert "final_score" in result
    assert result["total_required"] == 1
