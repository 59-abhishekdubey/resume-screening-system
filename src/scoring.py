# src/scoring.py
# Candidate scoring functions using Expanded-Skill-Weighted (ESW) formula.
# WEIGHTS module-level constant controls beta; user-editable without touching functions.

from __future__ import annotations

from src.skill_extraction import extract_skills


WEIGHTS = {"beta": 0.5}


def compute_required_skill_match(candidate_skills, required_skills) -> dict:
    """Compute which required skills are matched/missing.

    Returns {"matched": [...sorted], "missing": [...sorted], "ratio": float}.
    """
    candidate_set = set(candidate_skills)
    required_set = set(required_skills)

    matched = sorted(candidate_set & required_set)
    missing = sorted(required_set - candidate_set)

    total = len(required_set)
    ratio = len(matched) / total if total > 0 else 0.0

    return {"matched": matched, "missing": missing, "ratio": ratio}


def compute_additional_skills(candidate_skills, required, optional) -> dict:
    """Compute additional skills beyond required.

    Additional = skills in candidate ∩ (optional ∪ extra useful skills not in required).
    Returns {"matched_additional": [...], "total_additional": int}.
    """
    candidate_set = set(candidate_skills)
    optional_set = set(optional)

    matched_additional = sorted(candidate_set & optional_set)
    total_additional = len(optional_set)

    return {"matched_additional": matched_additional, "total_additional": total_additional}


def score_candidate(resume_profile, job_profile, similarity_score, weights=None) -> dict:
    """Score a candidate against a job profile using the ESW formula.

    weights defaults to module-level WEIGHTS; per-call override allowed.
    Returns dict with EVERY intermediate value.
    """
    if weights is None:
        weights = WEIGHTS

    beta = weights["beta"]

    # Extract skills from resume profile text
    resume_text = resume_profile.get("text", "")
    candidate_skills = extract_skills(resume_text) if resume_text else []

    # Get job skills
    if isinstance(job_profile, dict):
        required_skills = job_profile.get("required_skills", [])
        optional_skills = job_profile.get("optional_skills", [])
    else:
        required_skills = getattr(job_profile, "required_skills", [])
        optional_skills = getattr(job_profile, "optional_skills", [])

    # Compute required skill match
    required_match = compute_required_skill_match(candidate_skills, required_skills)
    matched_required = required_match["matched"]
    missing_required = required_match["missing"]
    tr_total = len(required_skills)  # total number of required skills

    # Compute additional skills
    additional = compute_additional_skills(candidate_skills, required_skills, optional_skills)
    matched_additional = additional["matched_additional"]
    ta = additional["total_additional"]

    # Compute skill component = (mr + β·ma) / (tr + β·ta)
    mr = len(matched_required)
    ma = len(matched_additional)

    # Handle edge cases per spec
    if tr_total == 0:
        skill_component = 1.0
    elif len(candidate_skills) == 0:
        skill_component = 0.0
    elif (tr_total + beta * ta) == 0:
        skill_component = 1.0
    else:
        skill_component = (mr + beta * ma) / (tr_total + beta * ta)

    # similarity_component
    similarity_component = similarity_score

    # final_score
    final_score = skill_component * similarity_component

    return {
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_additional": matched_additional,
        "total_required": tr_total,
        "total_additional": ta,
        "beta": beta,
        "skill_component": skill_component,
        "similarity_component": similarity_component,
        "final_score": final_score,
    }