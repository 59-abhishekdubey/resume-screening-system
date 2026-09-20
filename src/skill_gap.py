def compute_gap(candidate_skills: list[str], required_skills: list[str]) -> dict:
    candidate_set = set(candidate_skills)
    required_set = set(required_skills)
    matched = sorted(candidate_set & required_set)
    missing = sorted(required_set - candidate_set)
    return {"matched": matched, "missing": missing}


def coverage_ratio(matched: list[str], required: list[str]) -> float:
    if len(required) == 0:
        return 0.0
    return len(matched) / len(required)