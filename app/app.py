"""Flask screening app — Phase 10b. Replaces Streamlit UI.
Run: python app/app.py  (from repo root)  -> http://127.0.0.1:5000
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session, flash

# Ensure repo root on sys.path when launched as `python app/app.py`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.job_parser import parse_job  # noqa: E402
from src.pipeline import screen_resumes, screen_from_pdf_folder  # noqa: E402

# --- Verdict tunable constants (Phase 10c) ---
STRONG_SKILL_RATIO = 0.70
GOOD_SKILL_RATIO = 0.50
PARTIAL_SKILL_RATIO = 0.30
STRONG_RELATIVE = 0.70
GOOD_RELATIVE = 0.50
PARTIAL_RELATIVE = 0.30
HIGH_SIMILARITY = 0.50
MODERATE_SIMILARITY = 0.30
MISSING_DISPLAY_CAP = 4


def _verdict(skill_ratio: float, relative: float, similarity: float, matched_count: int, total_required: int, missing_skills: list, n_candidates: int) -> dict:
    """Compute human-readable verdict tier and deterministic reasoning."""
    # Branch 1 — total_required == 0: similarity-only tier
    if total_required == 0:
        if similarity >= HIGH_SIMILARITY:
            tier = "High textual overlap"
            css_class = "verdict-strong"
            short = "Resume has strong wording overlap with the JD."
            sim_sentence = "High textual overlap with the job description."
        elif similarity >= MODERATE_SIMILARITY:
            tier = "Moderate textual overlap"
            css_class = "verdict-partial"
            short = "Resume has moderate wording overlap with the JD."
            sim_sentence = "Moderate textual overlap with the job description."
        else:
            tier = "Low textual overlap"
            css_class = "verdict-weak"
            short = "Resume wording differs significantly from the JD."
            sim_sentence = "Low textual overlap \u2014 resume wording differs from the job description."
        reason = f"No required skills were specified for this role. {sim_sentence}"
        return {"tier": tier, "css_class": css_class, "reason": reason, "short": short}

    # Branch 2 — single candidate (and total_required > 0): skill_ratio only
    if n_candidates == 1:
        if skill_ratio >= STRONG_SKILL_RATIO:
            tier = "Strong skill overlap"
            css_class = "verdict-strong"
            short = "Most required skills present."
        elif skill_ratio >= GOOD_SKILL_RATIO:
            tier = "Good skill overlap"
            css_class = "verdict-good"
            short = "Most key skills present, some gaps."
        elif skill_ratio >= PARTIAL_SKILL_RATIO:
            tier = "Partial skill overlap"
            css_class = "verdict-partial"
            short = "Several required skills missing."
        else:
            tier = "Limited skill overlap"
            css_class = "verdict-weak"
            short = "Few required skills matched."
        parts = []
        parts.append(f"Found {matched_count} of {total_required} required skills.")
        if missing_skills:
            parts.append(f"Missing: {', '.join(sorted(missing_skills))}.")
        if similarity >= HIGH_SIMILARITY:
            parts.append("High textual overlap with the job description.")
        elif similarity >= MODERATE_SIMILARITY:
            parts.append("Moderate textual overlap with the job description.")
        else:
            parts.append("Low textual overlap \u2014 resume wording differs from the job description.")
        reason = " ".join(parts)
        return {"tier": tier, "css_class": css_class, "reason": reason, "short": short}

    # Branch 3 — normal (total_required > 0 AND n_candidates >= 2): keep [P10c] logic verbatim
    if skill_ratio >= STRONG_SKILL_RATIO and relative >= STRONG_RELATIVE:
        tier = "Strong skill overlap"
        css_class = "verdict-strong"
        short = "Most required skills present."
    elif skill_ratio >= GOOD_SKILL_RATIO or relative >= GOOD_RELATIVE:
        tier = "Good skill overlap"
        css_class = "verdict-good"
        short = "Most key skills present, some gaps."
    elif skill_ratio >= PARTIAL_SKILL_RATIO or relative >= PARTIAL_RELATIVE:
        tier = "Partial skill overlap"
        css_class = "verdict-partial"
        short = "Several required skills missing."
    else:
        tier = "Limited skill overlap"
        css_class = "verdict-weak"
        short = "Few required skills matched."

    parts = []
    parts.append(f"Found {matched_count} of {total_required} required skills.")
    if missing_skills:
        parts.append(f"Missing: {', '.join(sorted(missing_skills))}.")
    if similarity >= HIGH_SIMILARITY:
        parts.append("High textual overlap with the job description.")
    elif similarity >= MODERATE_SIMILARITY:
        parts.append("Moderate textual overlap with the job description.")
    else:
        parts.append("Low textual overlap \u2014 resume wording differs from the job description.")
    reason = " ".join(parts)

    return {"tier": tier, "css_class": css_class, "reason": reason, "short": short}


def _augment_result(result: dict, max_overall_score: float, n_candidates: int = 0) -> dict:
    """Return a COPY of result plus verdict keys without mutating original."""
    copy = dict(result)
    bd = result.get("score_breakdown", {})
    # Handle both list and count forms for matched_required per locked decisions
    matched_required_val = bd.get("matched_required", result.get("matched_skills", []))
    if isinstance(matched_required_val, list):
        matched_count = len(matched_required_val)
    else:
        try:
            matched_count = int(matched_required_val)
        except Exception:
            matched_count = len(result.get("matched_skills", []))
    total_required = bd.get("total_required", 0)
    if not isinstance(total_required, int):
        try:
            total_required = int(total_required)
        except Exception:
            total_required = 0
    skill_ratio = (matched_count / total_required) if total_required > 0 else 0.0
    relative = (result.get("overall_score", 0.0) / max_overall_score) if max_overall_score > 0 else 0.0
    similarity = result.get("similarity", 0.0)
    missing = result.get("missing_skills", [])
    v = _verdict(skill_ratio, relative, similarity, matched_count, total_required, missing, n_candidates)
    copy["verdict_tier"] = v["tier"]
    copy["verdict_css"] = v["css_class"]
    copy["verdict_reason"] = v["reason"]
    copy["verdict_short"] = v["short"]
    # Missing skills display line (Phase 10d) — capped, prefix "Missing: "
    if not missing:
        copy["verdict_missing_line"] = ""
    elif len(missing) <= MISSING_DISPLAY_CAP:
        copy["verdict_missing_line"] = "Missing: " + ", ".join(missing)
    else:
        shown = missing[:MISSING_DISPLAY_CAP]
        remaining = len(missing) - MISSING_DISPLAY_CAP
        copy["verdict_missing_line"] = "Missing: " + ", ".join(shown) + f" +{remaining} more"
    # Display-only fields for recruiter UI (Phase 10e/10f) — not stored in session
    if total_required == 0:
        copy["skill_coverage_display"] = "No required skills specified for this role"
        copy["skill_coverage_pct"] = ""
    else:
        copy["skill_coverage_display"] = f"{matched_count} / {total_required} required skills"
        pct = round(100 * matched_count / total_required, 1) if total_required else 0.0
        copy["skill_coverage_pct"] = f"{pct:.1f}%"
    copy["jd_similarity_display"] = f"{round(similarity * 100, 1):.1f}%"
    # Why-this-result bullets (deterministic, no LLM) — per branch
    if total_required == 0:
        if similarity >= HIGH_SIMILARITY:
            bullets = ["The resume has high textual overlap with the JD.", "No required skills were specified for this role."]
        elif similarity >= MODERATE_SIMILARITY:
            bullets = ["Resume-to-job textual similarity was moderate.", "No required skills were specified for this role."]
        else:
            bullets = ["Resume wording differs from the job description.", "No required skills were specified for this role."]
    else:
        bullets = []
        bullets.append(f"Matched {matched_count} of {total_required} required skills.")
        if missing:
            bullets.append(f"Missing required skills: {', '.join(sorted(missing))}.")
        if similarity >= HIGH_SIMILARITY:
            bullets.append("The resume has high textual overlap with the JD.")
        elif similarity >= MODERATE_SIMILARITY:
            bullets.append("Resume-to-job textual similarity was moderate.")
        else:
            bullets.append("Resume-to-job textual similarity was low.")
        matched_additional_val = bd.get("matched_additional", [])
        if isinstance(matched_additional_val, list):
            add_count = len(matched_additional_val)
        else:
            try:
                add_count = int(matched_additional_val)
            except Exception:
                add_count = 0
        if add_count > 0:
            bullets.append(f"Also found {add_count} additional relevant skill(s) beyond the required set.")
    # Ensure at least one bullet
    if not bullets:
        bullets = ["No required skills were specified for this role."]
    copy["why_result_bullets"] = bullets
    return copy


app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-prod-10b"

# --- resolve sample jobs path ---
CANDIDATE_PATHS = [
    ROOT / "data" / "raw" / "sample_jobs.json",
    ROOT / "data" / "job_descriptions" / "sample_jobs.json",
]
SAMPLE_JOBS_PATH = next((p for p in CANDIDATE_PATHS if p.exists()), CANDIDATE_PATHS[0])


def load_sample_jobs():
    if not SAMPLE_JOBS_PATH.exists():
        return []
    try:
        return json.loads(SAMPLE_JOBS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def get_roles_and_jobs():
    jobs = load_sample_jobs()
    roles = [j.get("role", "") for j in jobs]
    return jobs, roles


@app.route("/", methods=["GET"])
def index():
    _, roles = get_roles_and_jobs()
    return render_template("index.html", roles=roles)


@app.route("/screen", methods=["POST"])
def screen():
    jobs, roles = get_roles_and_jobs()

    # --- Job input ---
    custom_jd = (request.form.get("custom_jd") or "").strip()
    selected_role = (request.form.get("job_role") or "").strip()
    role_override = (request.form.get("role_override") or "").strip()

    job_dict_to_parse = None

    if custom_jd:
        role = role_override or "Custom Role"
        job_dict_to_parse = {
            "role": role,
            "description": custom_jd,
            "required_skills": [],
            "optional_skills": [],
        }
    elif selected_role:
        sel_job = next((j for j in jobs if j.get("role") == selected_role), None)
        if sel_job is None:
            flash("Selected job role not found. Please select a valid role or paste a JD.")
            return render_template("index.html", roles=roles)
        if role_override:
            sel_job = {**sel_job, "role": role_override}
        job_dict_to_parse = sel_job
    else:
        flash("Provide a job first: select a sample job or paste a JD (non-empty).")
        return render_template("index.html", roles=roles)

    # Validate job description non-empty
    desc_for_check = (job_dict_to_parse.get("description") or "").strip()
    if not desc_for_check:
        flash("Job description is empty — paste a JD or select a valid sample job.")
        return render_template("index.html", roles=roles)

    # --- Resume input ---
    resume_text = (request.form.get("resume_text") or "").strip()
    paste_cid = (request.form.get("candidate_id") or "").strip() or "PASTE_001"
    uploaded_files = request.files.getlist("pdfs")

    # Filter valid files (non-empty filename)
    has_pdf_upload = any((f.filename or "").strip() for f in uploaded_files)

    # Parse job first (needed for both branches)
    try:
        job_profile = parse_job(job_dict_to_parse)
    except Exception as e:
        flash(f"Job parsing failed: {e}")
        return render_template("index.html", roles=roles)

    results = None

    if has_pdf_upload:
        # Validate extensions — reject non-PDF gracefully
        valid_pdfs = []
        invalid_names = []
        for f in uploaded_files:
            fname = (f.filename or "").strip()
            if not fname:
                continue
            if not fname.lower().endswith(".pdf"):
                invalid_names.append(fname)
            else:
                valid_pdfs.append(f)

        if invalid_names and not valid_pdfs and not resume_text:
            flash("Please upload a PDF file.")
            return render_template("index.html", roles=roles)

        if not valid_pdfs and not resume_text:
            flash("No resumes ready — upload at least one PDF or paste resume text.")
            return render_template("index.html", roles=roles)

        if valid_pdfs:
            # Save to tempdir and call screen_from_pdf_folder
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    for f in valid_pdfs:
                        fname = Path(f.filename).name
                        # sanitize filename
                        dest = Path(tmpdir) / fname
                        f.save(str(dest))
                    results = screen_from_pdf_folder(job_profile, tmpdir)
                    # If only PDFs were provided but all extractions empty
                    if not results:
                        if invalid_names:
                            flash(f"No valid resumes extracted. Invalid files skipped: {', '.join(invalid_names)}.")
                        else:
                            flash("No resumes extracted — PDFs may be empty or image-only.")
                        return render_template("index.html", roles=roles)
                    # Also handle case where user pasted text + PDFs: PDFs take precedence per spec
                    # If resume_text also provided, we ignore it when PDFs present (or could combine)
            except Exception as e:
                flash(f"Screening failed: {e}")
                return render_template("index.html", roles=roles)
        else:
            # No valid PDFs but resume_text exists — fall through to text branch
            has_pdf_upload = False

    if results is None:
        # Text branch: single pasted resume
        if not resume_text:
            # Guard: also check if we had invalid PDFs already handled
            flash("No resume text — paste resume content and ensure Candidate ID is non-empty.")
            return render_template("index.html", roles=roles)
        resumes_for_screening = [{"candidate_id": paste_cid, "text": resume_text}]
        try:
            results = screen_resumes(job_profile, resumes_for_screening)
        except Exception as e:
            flash(f"Screening failed: {e}")
            return render_template("index.html", roles=roles)
        if not results:
            flash("No results produced — check resume text.")
            return render_template("index.html", roles=roles)

    # Store minimal keys in session (no raw resume text)
    session_results = []
    for r in results:
        session_results.append({
            "rank": r["rank"],
            "candidate_id": r["candidate_id"],
            "overall_score": r["overall_score"],
            "matched_skills": r["matched_skills"],
            "missing_skills": r["missing_skills"],
            "similarity": r["similarity"],
            "score_breakdown": r["score_breakdown"],
            "explanation": r["explanation"],
        })

    session["results"] = session_results
    session["job_role"] = job_profile.role
    # Store max for internal verdict relative calculation (not for template display) and n_candidates for Branch 2
    session["max_score"] = max((x["overall_score"] for x in session_results), default=0.0)
    session["n_candidates"] = len(session_results)

    return redirect(url_for("results"))


@app.route("/results", methods=["GET"])
def results():
    results_data = session.get("results")
    if not results_data:
        flash("No results yet — select a job and add resumes, then click Run Screening.")
        _, roles = get_roles_and_jobs()
        return render_template("index.html", roles=roles)
    job_role = session.get("job_role", "—")
    max_score = session.get("max_score", 0.0)
    if max_score == 0:
        max_score = max((r["overall_score"] for r in results_data), default=0.0)
    n_candidates = session.get("n_candidates", len(results_data))
    # Augment with display fields (computed in route, not stored in session)
    augmented = [_augment_result(r, max_score, n_candidates=n_candidates) for r in results_data]
    return render_template("result.html", results=augmented, job_role=job_role)


@app.route("/candidate/<candidate_id>", methods=["GET"])
def candidate(candidate_id):
    results_data = session.get("results")
    if not results_data:
        flash("No results in session — run a screening first.")
        return redirect(url_for("index"))
    selected = next((r for r in results_data if r["candidate_id"] == candidate_id), None)
    if selected is None:
        flash(f"Candidate {candidate_id} not found.")
        return redirect(url_for("results"))
    max_score = session.get("max_score", 0.0)
    if max_score == 0:
        max_score = max((r["overall_score"] for r in results_data), default=0.0)
    n_candidates = session.get("n_candidates", len(results_data))
    augmented = _augment_result(selected, max_score, n_candidates=n_candidates)
    return render_template("candidate.html", candidate=augmented, job_role=session.get("job_role", "—"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
