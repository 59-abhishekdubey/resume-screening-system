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
            flash(f"Non-PDF upload rejected: {', '.join(invalid_names)} — please upload .pdf files only.")
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
    # Store max for relative display (computed again in /results but keep for convenience)
    session["max_score"] = max((x["overall_score"] for x in session_results), default=0.0)

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
    return render_template("result.html", results=results_data, job_role=job_role, max_score=max_score)


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
    # DISPLAY NORMALIZATION (Option C): relative = overall_score / max_overall_score per run
    # Raw overall_score is preserved verbatim; relative is for visual bars only.
    relative = (selected["overall_score"] / max_score) if max_score > 0 else 0.0
    return render_template("candidate.html", candidate=selected, max_score=max_score, relative=relative, job_role=session.get("job_role", "—"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
