"""Pipeline orchestration: JD + resumes -> ranked, explained results."""
from __future__ import annotations

import json
import os
import sys

from src.job_parser import JobProfile, parse_job
from src.pdf_parser import extract_text_from_pdfs
from src.preprocessing import clean_text
from src.scoring import WEIGHTS, score_candidate
from src.similarity import tfidf_similarity
from src.skill_gap import coverage_ratio


def _normalize_job(job) -> JobProfile:
    """Convert JobProfile | dict to JobProfile.

    Accepted shapes:
    - JobProfile dataclass instance (returned as-is)
    - dict with keys ``clean_description`` + ``required_skills`` (already a JobProfile-like dict)
    - raw job dict with ``role`` / ``description`` / ``required_skills`` / ``optional_skills``
      (delegated to ``parse_job``)
    """
    if isinstance(job, JobProfile):
        return job
    if isinstance(job, dict):
        if "clean_description" in job and "required_skills" in job:
            return JobProfile(
                role=job.get("role", ""),
                clean_description=job.get("clean_description", ""),
                required_skills=list(job.get("required_skills", [])),
                optional_skills=list(job.get("optional_skills", [])),
                raw_text=job.get("raw_text", ""),
            )
        return parse_job(job)
    raise TypeError("job must be JobProfile or dict")


def build_candidate_result(
    candidate_id,
    job_profile,
    similarity_score,
    score_dict,
) -> dict:
    matched_required = score_dict["matched_required"]
    missing_required = score_dict["missing_required"]
    matched_additional = score_dict["matched_additional"]

    explanation = generate_explanation(
        {
            "matched_skills": matched_required,
            "missing_skills": missing_required,
            "additional_skills": matched_additional,
            "similarity": similarity_score,
        }
    )

    result = {
        "candidate_id": candidate_id,
        "overall_score": score_dict["final_score"],
        "similarity": similarity_score,
        "matched_skills": matched_required,
        "missing_skills": missing_required,
        "score_breakdown": score_dict,
        "explanation": explanation,
    }
    return result


def generate_explanation(result: dict) -> str:
    parts = []

    matched = result["matched_skills"]
    missing = result["missing_skills"]
    similarity = result["similarity"]

    req = matched + missing

    if coverage_ratio(matched, req) >= 0.8:
        parts.append("Strong required-skill coverage")

    if similarity >= 0.6:
        parts.append("High similarity to job description")
    elif similarity >= 0.35:
        parts.append("Moderate similarity to job description")

    if missing:
        parts.append("Missing: " + ", ".join(sorted(missing)))

    if not parts:
        return "Insufficient signal to explain ranking"

    return "; ".join(parts)


def screen_resumes(job: JobProfile | dict, resumes: list[dict], weights=None) -> list[dict]:
    """Screen resumes against a job profile.

    Flow: clean -> similarity -> score -> rank -> explain
    Skill extraction and gap are delegated to score_candidate to avoid duplication.

    Args:
        job: JobProfile instance or dict (raw job JSON or JobProfile-like dict).
        resumes: list of {"candidate_id": str, "text": str}
        weights: optional weights dict, defaults to scoring.WEIGHTS ({"beta": 0.5})

    Returns:
        Ranked list of dicts (highest score first). Each dict contains exactly:
        rank, candidate_id, overall_score, matched_skills, missing_skills,
        similarity, score_breakdown, explanation
    """
    if weights is None:
        weights = WEIGHTS

    if not resumes:
        return []

    job_profile = _normalize_job(job)
    jd_text = job_profile.clean_description or ""

    intermediates: list[tuple[str, float, dict]] = []
    for entry in resumes:
        candidate_id = str(entry.get("candidate_id", ""))
        text = entry.get("text", "") or ""

        cleaned = clean_text(text)
        similarity_score = tfidf_similarity(cleaned, jd_text)

        resume_profile = {"candidate_id": candidate_id, "text": text}
        score_dict = score_candidate(resume_profile, job_profile, similarity_score, weights=weights)

        intermediates.append((candidate_id, similarity_score, score_dict))

    intermediates.sort(key=lambda x: (-x[2]["final_score"], x[0]))

    results: list[dict] = []
    for idx, (candidate_id, similarity_score, score_dict) in enumerate(intermediates, start=1):
        tmp = build_candidate_result(
            candidate_id,
            job_profile,
            similarity_score,
            score_dict,
        )
        final = {
            "rank": idx,
            "candidate_id": tmp["candidate_id"],
            "overall_score": tmp["overall_score"],
            "matched_skills": tmp["matched_skills"],
            "missing_skills": tmp["missing_skills"],
            "similarity": tmp["similarity"],
            "score_breakdown": tmp["score_breakdown"],
            "explanation": tmp["explanation"],
        }
        results.append(final)

    return results


def screen_from_pdf_folder(job: JobProfile | dict, pdf_folder: str, weights=None) -> list[dict]:
    """Wraps extract_text_from_pdfs + screen_resumes.

    Args:
        job: JobProfile instance or dict.
        pdf_folder: path to folder containing resume PDFs.
        weights: optional weights dict.

    Returns:
        Ranked list of dicts (same shape as screen_resumes).

    Notes:
        - candidate_id = PDF filename stem (e.g. "16852973")
        - PDFs whose extraction returns "" are skipped with a warning on stderr.
        - Results are sorted deterministically by filename stem handling.
    """
    if weights is None:
        weights = WEIGHTS

    texts = extract_text_from_pdfs(pdf_folder)
    resumes: list[dict] = []
    for stem in sorted(texts.keys()):
        text = texts[stem]
        if not text or not text.strip():
            print(f"Warning: empty extraction for {stem}.pdf — skipping.", file=sys.stderr)
            continue
        resumes.append({"candidate_id": stem, "text": text})

    return screen_resumes(job, resumes, weights=weights)


def save_screening_report(results: list[dict], path: str = "outputs/results/screening_report.json") -> None:
    """Write ranked results to JSON.

    Args:
        results: list of dicts returned by screen_resumes / screen_from_pdf_folder.
        path: output file path (default "outputs/results/screening_report.json").
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
