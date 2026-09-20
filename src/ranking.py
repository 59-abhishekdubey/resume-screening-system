# src/ranking.py
# Candidate ranking functions using similarity + skill signals.

from __future__ import annotations

from src import similarity
from src.preprocessing import clean_text
from src.skill_extraction import extract_skills
from src.scoring import score_candidate, WEIGHTS


def rank_candidates(
    candidates: list[dict],
    job: "JobProfile",
    weights=None,
    method: str = "tfidf",
) -> list[dict]:
    """Rank candidates against a job profile.

    candidates = [{"candidate_id": ..., "text": ...}, ...]
    Internally: clean → extract_skills → similarity → score → sort by final_score desc.

    Each output dict contains: rank, candidate_id, final_score, similarity_score,
      matched_required, missing_required, matched_additional, score_breakdown.
    """
    if weights is None:
        weights = WEIGHTS

    method = method.lower()
    ranked = []

    for idx, cand in enumerate(candidates):
        candidate_id = cand.get("candidate_id", idx)
        text = cand.get("text", "")

        # Compute similarity
        cleaned = clean_text(text)
        if method == "tfidf":
            sim = similarity.tfidf_similarity(cleaned, job.clean_description)
        elif method == "semantic":
            sim = similarity.semantic_similarity(cleaned, job.clean_description)
        else:
            raise ValueError(f'Unknown method "{method}"; use "tfidf" or "semantic"')

        # Score candidate
        profile = {
            "candidate_id": candidate_id,
            "text": text,
        }
        score = score_candidate(profile, job, sim, weights=weights)

        ranked.append(
            {
                "rank": 0,  # will be set after sorting
                "candidate_id": candidate_id,
                "final_score": score["final_score"],
                "similarity_score": sim,
                "matched_required": score["matched_required"],
                "missing_required": score["missing_required"],
                "matched_additional": score["matched_additional"],
                "score_breakdown": score,
            }
        )

    # Sort by final_score descending
    ranked.sort(key=lambda x: x["final_score"], reverse=True)

    # Assign ranks (dense ranking: same scores get same rank)
    for i, entry in enumerate(ranked):
        entry["rank"] = i + 1

    return ranked


def save_rankings(ranked: list[dict], path: str = "outputs/results/candidate_rankings.csv") -> None:
    """Write ranked candidates to CSV, one row per candidate with all breakdown columns flattened."""
    import csv

    # Collect all possible column names from score_breakdown keys
    # and top-level fields
    score_breakdown_keys = [
        "matched_required",
        "missing_required",
        "matched_additional",
        "total_required",
        "total_additional",
        "beta",
        "skill_component",
        "similarity_component",
        "final_score",
    ]

    fieldnames = [
        "rank",
        "candidate_id",
        "final_score",
        "similarity_score",
    ] + score_breakdown_keys

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for entry in ranked:
            row = {
                "rank": entry["rank"],
                "candidate_id": entry["candidate_id"],
                "final_score": entry["final_score"],
                "similarity_score": entry["similarity_score"],
            }
            sb = entry["score_breakdown"]
            for key in score_breakdown_keys:
                val = sb.get(key, "")
                # Convert lists to comma-joined strings for CSV
                if isinstance(val, list):
                    val = ", ".join(val)
                row[key] = val
            writer.writerow(row)