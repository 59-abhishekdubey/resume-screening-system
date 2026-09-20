import pytest
from src.skill_gap import compute_gap, coverage_ratio


# --- original self-checks preserved as pytest tests ---

def test_compute_gap_missing_aws():
    result = compute_gap(["Python", "SQL"], ["Python", "SQL", "AWS"])
    assert result["missing"] == ["AWS"]
    assert result["matched"] == ["Python", "SQL"]


def test_coverage_ratio_empty_required():
    assert coverage_ratio([], []) == 0.0
    assert coverage_ratio(["Python"], []) == 0.0


def test_coverage_ratio_normal():
    assert coverage_ratio(["Python"], ["Python", "SQL"]) == 0.5


def test_compute_gap_dedup():
    result = compute_gap(["Python", "Python", "SQL"], ["Python", "SQL", "AWS"])
    assert result["matched"] == ["Python", "SQL"]
    assert result["missing"] == ["AWS"]


# --- additional edge-case tests per Phase 11 spec ---

def test_compute_gap_exact_spec_example():
    # compute_gap({"Python","SQL"}, {"Python","SQL","AWS"}) -> missing == ["AWS"]
    result = compute_gap({"Python", "SQL"}, {"Python", "SQL", "AWS"})
    assert result["missing"] == ["AWS"]
    assert result["matched"] == ["Python", "SQL"]


def test_coverage_ratio_no_zero_division():
    # empty required should not raise ZeroDivisionError
    try:
        r = coverage_ratio([], [])
        assert r == 0.0
    except ZeroDivisionError:
        pytest.fail("coverage_ratio raised ZeroDivisionError on empty required")
    try:
        r = coverage_ratio(["Python"], [])
        assert r == 0.0
    except ZeroDivisionError:
        pytest.fail("coverage_ratio raised ZeroDivisionError on empty required with non-empty matched")


def test_duplicate_skills_deduped_gap():
    result = compute_gap(["Python", "Python", "SQL", "SQL"], ["Python", "SQL", "AWS", "AWS"])
    assert result["matched"] == ["Python", "SQL"]
    assert result["missing"] == ["AWS"]


def test_duplicate_required_deduped():
    result = compute_gap(["Python"], ["Python", "Python", "SQL", "SQL"])
    assert result["missing"] == ["SQL"]
    assert result["matched"] == ["Python"]


def test_coverage_ratio_returns_float_in_range():
    assert coverage_ratio(["Python", "SQL"], ["Python", "SQL", "AWS"]) == pytest.approx(2/3)
    assert 0.0 <= coverage_ratio([], ["Python"]) <= 1.0


def test_compute_gap_empty_inputs():
    result = compute_gap([], [])
    assert result["matched"] == []
    assert result["missing"] == []
    result2 = compute_gap([], ["Python"])
    assert result2["missing"] == ["Python"]
