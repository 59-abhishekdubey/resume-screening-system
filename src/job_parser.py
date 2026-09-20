import json
import re
from dataclasses import dataclass, field
from typing import Any

from src.preprocessing import clean_text
from src.skill_extraction import extract_skills
from src.config import SKILL_VOCABULARY, SKILL_ALIASES


def normalize_skill(skill_str: str) -> str:
    """Normalize a skill string to its canonical form using the config vocabulary."""
    if not skill_str:
        return skill_str
    lower = skill_str.strip().lower()
    if lower in SKILL_ALIASES:
        return SKILL_ALIASES[lower]
    for canonical, aliases in SKILL_VOCABULARY.items():
        if lower in aliases:
            return canonical
    for part in lower.split():
        if part in SKILL_ALIASES:
            return SKILL_ALIASES[part]
    return skill_str.strip()


def _parse_section_skills(text: str, target_header: str) -> list[str]:
    """Extract skills following a specific section header.

    Looks for known section headers: "Requirements:", "Nice to have:",
    "Preferred:". Skills under the target header are collected; encountering
    a different known header stops collection.
    """
    skills: list[str] = []
    lines = text.split("\n")
    in_section = False

    # Normalize target header for comparison
    target = target_header.strip()
    target_upper = target.upper()
    target_colon_upper = (target + ":").upper()

    # Known header patterns: header name -> list of possible upper-cased forms
    header_patterns = {
        "REQUIREMENTS": {"REQUIREMENTS:", "REQUIREMENTS"},
        "NICE_TO_HAVE": {"NICE TO HAVE:", "NICE TO HAVE"},
        "PREFERRED": {"PREFERRED:", "PREFERRED"},
    }

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        upper = stripped.upper()

        # Check if this line is a known section header
        is_known_header = False
        for _hname, patterns in header_patterns.items():
            if upper in patterns:
                is_known_header = True
                break

        if is_known_header:
            # Check if this is the target header
            if upper == target_colon_upper or upper == target_upper:
                in_section = True
            else:
                # Different known header — stop collecting for the target
                in_section = False
            continue

        if in_section:
            # Remove bullet markers (-, •, *) and extract skill text
            skill = re.sub(r"^[-•*]\s*", "", stripped)
            if skill:
                skills.append(skill)

    return skills


def extract_job_skills(text: str) -> dict[str, list[str]]:
    """Extract required and optional skills from job description text based on section headers.

    Parses section headers "Requirements:", "Nice to have:", "Preferred:"
    and categorizes skills accordingly. "Preferred:" skills are mapped to "optional".

    Returns:
        dict with keys "required" and "optional" containing lists of raw skill strings.
    """
    required: list[str] = []
    optional: list[str] = []

    # Parse Requirements section -> required
    req_skills = _parse_section_skills(text, "Requirements")
    required.extend(req_skills)

    # Parse Nice to have section -> optional
    nice_skills = _parse_section_skills(text, "Nice to have")
    optional.extend(nice_skills)

    # Parse Preferred section -> optional (mapped from Preferred)
    pref_skills = _parse_section_skills(text, "Preferred")
    optional.extend(pref_skills)

    # Normalize all skills using the config vocabulary
    norm_required = [normalize_skill(s) for s in required]
    norm_optional = [normalize_skill(s) for s in optional]

    # Deduplicate while preserving order
    seen_req: set[str] = set()
    seen_opt: set[str] = set()
    dedup_required: list[str] = []
    dedup_optional: list[str] = []

    for s in norm_required:
        if s not in seen_req:
            seen_req.add(s)
            dedup_required.append(s)

    for s in norm_optional:
        if s not in seen_opt:
            seen_opt.add(s)
            dedup_optional.append(s)

    return {
        "required": dedup_required,
        "optional": dedup_optional,
    }


@dataclass
class JobProfile:
    role: str
    clean_description: str
    required_skills: list[str] = field(default_factory=list)
    optional_skills: list[str] = field(default_factory=list)
    raw_text: str = ""


def parse_job(json_path_or_dict: Any) -> JobProfile:
    """Parse a job description from a JSON dict or file path and return a JobProfile.

    Internal process:
    1. Load JSON data from path or dict
    2. Run clean_text() from src.preprocessing on the description
    3. Run extract_skills() from src.skill_extraction on the cleaned text
    4. Normalize and merge with declared required/optional skill lists
    5. Declared fields are authoritative (always included even if absent from text)
    """
    if isinstance(json_path_or_dict, str):
        with open(json_path_or_dict, "r") as f:
            data = json.load(f)
    else:
        data = json_path_or_dict

    role = data["role"]
    raw_description = data["description"]
    raw_required = data.get("required_skills", [])
    raw_optional = data.get("optional_skills", [])

    # Step 2: Clean the description text
    clean_desc = clean_text(raw_description)

    # Step 3: Extract skills from cleaned text
    extracted = extract_skills(clean_desc)

    # Step 4: Normalize declared skills using the config vocabulary
    norm_required = [normalize_skill(s) for s in raw_required]
    norm_optional = [normalize_skill(s) for s in raw_optional]

    # Step 5: Build final skill lists
    # Authoritative: all declared required skills are always included
    final_required: list[str] = list(norm_required)

    # Authoritative: all declared optional skills are always included
    final_optional: list[str] = list(norm_optional)

    # Add extracted skills that aren't already in either list (default to optional)
    for skill in extracted:
        if skill not in final_required and skill not in final_optional:
            final_optional.append(skill)

    # Deduplicate while preserving order (declared first, then newly added)
    seen_req: set[str] = set()
    seen_opt: set[str] = set()
    dedup_required: list[str] = []
    dedup_optional: list[str] = []

    for s in final_required:
        if s not in seen_req:
            seen_req.add(s)
            dedup_required.append(s)

    for s in final_optional:
        if s not in seen_opt:
            seen_opt.add(s)
            dedup_optional.append(s)

    return JobProfile(
        role=role,
        clean_description=clean_desc,
        required_skills=dedup_required,
        optional_skills=dedup_optional,
        raw_text=raw_description,
    )