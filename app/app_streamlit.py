# Archived Streamlit UI from Phase 10. Superseded by Flask app.py (Phase 10b).
"""Recruiter screening dashboard — Phase 10.
Single-file Streamlit app that delegates all scoring to src/pipeline.py.
Run: streamlit run app/app.py  (from repo root)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

# Ensure repo root on sys.path when launched as `streamlit run app/app.py`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.job_parser import parse_job  # noqa: E402
from src.pipeline import screen_resumes  # noqa: E402

# No semantic model caching needed: pipeline uses only tfidf_similarity
# per [P9] src/pipeline.py:128 and src/similarity.py:28

st.set_page_config(page_title="AI Candidate Screening", layout="wide")

# --- session state init ---
for k, v in {
    "results": [],
    "selected_id": None,
    "job_profile": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- resolve sample jobs path ---
# Spec asks to verify data/raw/sample_jobs.json vs data/job_descriptions/sample_jobs.json
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

SAMPLE_JOBS = load_sample_jobs()
SAMPLE_ROLES = [j.get("role", "") for j in SAMPLE_JOBS]

st.title("AI Candidate Screening")
st.caption("Evidence-first ranking — matched/missing skills, similarity, and explainability from `src/pipeline.py`.")

# ============================================================
# Screen 1 — Job Input
# ============================================================
st.header("1 — Job Input")
col_a, col_b = st.columns([2, 1])

with col_a:
    job_mode = st.radio(
        "Job source",
        ["Select sample job", "Paste JD text"],
        horizontal=True,
        key="job_mode",
    )

with col_b:
    role_override = st.text_input(
        "Optional role label (overrides pasted JD role)",
        placeholder="e.g. ML Engineer — Custom",
        key="role_override",
    )

job_dict_to_parse = None
jd_preview = ""

if job_mode == "Select sample job":
    if not SAMPLE_JOBS:
        st.warning(f"No sample jobs found at {SAMPLE_JOBS_PATH}. Use 'Paste JD text'.")
    else:
        sel_role = st.selectbox("Sample role", SAMPLE_ROLES, key="sample_role")
        sel_job = next((j for j in SAMPLE_JOBS if j.get("role") == sel_role), SAMPLE_JOBS[0])
        # Allow role override to rename without mutating required skills
        if role_override.strip():
            sel_job = {**sel_job, "role": role_override.strip()}
        job_dict_to_parse = sel_job
        jd_preview = sel_job.get("description", "")
        with st.expander("Preview selected JD", expanded=False):
            st.write(f"**Role:** {sel_job.get('role','')}")
            st.write(f"**Required:** {', '.join(sel_job.get('required_skills',[])) or '—'}")
            st.write(f"**Optional:** {', '.join(sel_job.get('optional_skills',[])) or '—'}")
            st.text_area("Description", jd_preview, height=180, disabled=True, key="preview_desc")
else:
    pasted_jd = st.text_area(
        "Paste job description (free text)",
        height=200,
        placeholder="Paste the full JD here — Requirements / Preferred sections will be parsed if present, otherwise skills are extracted from the text.",
        key="pasted_jd",
    )
    # parse_job requires role + description + skill lists; for free-text JD we provide empty skill lists
    # and let extract_skills handle detection — declared lists remain authoritative per src/job_parser.py:169
    if pasted_jd and pasted_jd.strip():
        role = role_override.strip() or "Custom Role"
        job_dict_to_parse = {
            "role": role,
            "description": pasted_jd.strip(),
            "required_skills": [],
            "optional_skills": [],
        }
        jd_preview = pasted_jd.strip()

# ============================================================
# Screen 2 — Resume Input
# ============================================================
st.divider()
st.header("2 — Resume Input")

resume_mode = st.radio(
    "Resume source",
    ["Upload PDFs (multi-file)", "Paste resume text (single quick test)"],
    horizontal=True,
    key="resume_mode",
)

resumes_for_screening: list[dict] = []
resume_errors: list[str] = []

if resume_mode == "Upload PDFs (multi-file)":
    uploads = st.file_uploader(
        "Upload resume PDFs (fixture PDFs in data/raw/pdfs/*.pdf work here)",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_uploads",
        help="Only .pdf files accepted. Non-PDF uploads are rejected without crashing.",
    )
    pasted_resume_single = ""  # unused in this mode
    if uploads:
        for f in uploads:
            name = f.name or "unknown.pdf"
            # Hard guard: non-PDF extension (Streamlit type filter can be bypassed)
            if not name.lower().endswith(".pdf"):
                resume_errors.append(f"{name}: not a PDF — skipped.")
                continue
            try:
                import pdfplumber

                # pdfplumber works with file-like; need to seek to 0
                f.seek(0)
                text = ""
                with pdfplumber.open(f) as pdf:
                    if getattr(pdf, "is_encrypted", False):
                        resume_errors.append(f"{name}: encrypted PDF — skipped.")
                        continue
                    for page in pdf.pages:
                        t = page.extract_text() or ""
                        text += t + "\n"
                text = text.strip()
                if not text:
                    resume_errors.append(f"{name}: empty extraction — skipped.")
                    continue
                stem = Path(name).stem
                resumes_for_screening.append({"candidate_id": stem, "text": text})
            except Exception as e:
                resume_errors.append(f"{name}: extraction failed ({e}) — skipped.")
                continue
        if resumes_for_screening:
            st.success(f"Ready: {len(resumes_for_screening)} PDF(s) extracted.")
        if resume_errors:
            for msg in resume_errors:
                st.warning(msg)
else:
    # single paste mode
    pasted_resume_single = st.text_area(
        "Paste single resume text",
        height=200,
        placeholder="Paste raw resume text here for a quick single-candidate test.",
        key="pasted_resume",
    )
    paste_cid = st.text_input("Candidate ID for pasted resume", value="PASTE_001", key="paste_cid")
    uploads = []
    if pasted_resume_single and pasted_resume_single.strip():
        cid = paste_cid.strip() or "PASTE_001"
        resumes_for_screening = [{"candidate_id": cid, "text": pasted_resume_single.strip()}]
        st.info(f"Ready: 1 pasted resume as '{cid}'.")

# ============================================================
# Run Screening
# ============================================================
st.divider()
st.header("3 — Results")

run_clicked = st.button("Run Screening", type="primary", use_container_width=True)

if run_clicked:
    # --- validations (handle empty inputs without stack trace) ---
    if job_dict_to_parse is None:
        st.error("Provide a job first: select a sample job or paste a JD (non-empty).")
        st.stop()
    # job_dict_to_parse may have empty description if user switched modes
    desc_for_check = job_dict_to_parse.get("description", "") or ""
    if not desc_for_check.strip():
        st.error("Job description is empty — paste a JD or select a valid sample job.")
        st.stop()
    if not resumes_for_screening:
        if resume_mode == "Upload PDFs (multi-file)":
            st.error("No resumes ready — upload at least one PDF (or fix extraction warnings above).")
        else:
            st.error("No resume text — paste resume content and ensure Candidate ID is non-empty.")
        st.stop()

    # --- build JobProfile and call pipeline (sole entry point) ---
    try:
        job_profile = parse_job(job_dict_to_parse)
    except Exception as e:
        st.error(f"Job parsing failed: {e}")
        st.stop()

    try:
        # Single entry point per hard constraint — no reimplementation of scoring/ranking
        results = screen_resumes(job_profile, resumes_for_screening)
    except Exception as e:
        st.error(f"Screening failed: {e}")
        st.stop()

    st.session_state["results"] = results
    st.session_state["job_profile"] = job_profile
    # default selection to rank 1
    st.session_state["selected_id"] = results[0]["candidate_id"] if results else None
    st.success(f"Screened {len(results)} candidate(s) for role '{job_profile.role}'.")

results: list[dict] = st.session_state.get("results", [])

if not results:
    st.info("No results yet — select/paste a JD, add resumes, then click **Run Screening**.")
    st.stop()

# --- compute display normalization (Option C) ---
# DISPLAY NORMALIZATION (Option C): relative = overall_score / max_overall_score per run
# Raw overall_score is preserved verbatim; relative is for visual bars only and not
# presented as an absolute percentage. Comment required by hard constraint.
max_score = max((r["overall_score"] for r in results), default=0.0)
min_score = min((r["overall_score"] for r in results), default=0.0)

def relative_score(raw: float) -> float:
    if max_score <= 0:
        return 0.0
    return raw / max_score

# Build display dataframe
# Rank | Candidate ID | Match (per display choice) | Similarity
# Option C: Match = Relative bar (0..1) + raw in tooltip; Similarity raw number not %
rows = []
for r in results:
    raw = r["overall_score"]
    rel = relative_score(raw)
    rows.append(
        {
            "Rank": r["rank"],
            "Candidate ID": r["candidate_id"],
            "Relative Match": rel,
            "Raw Match": raw,
            "Similarity": r["similarity"],
        }
    )

df = pd.DataFrame(rows)

# Show summary caption
st.caption(
    f"Role: **{st.session_state['job_profile'].role}** — "
    f"{len(results)} candidates — max raw {max_score:.4f}, "
    f"min {min_score:.4f} — relative bars = raw / max (Option C)."
)

# Ranked table with progress bar for Relative Match
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn("Rank", width="small"),
        "Candidate ID": st.column_config.TextColumn("Candidate ID", width="medium"),
        "Relative Match": st.column_config.ProgressColumn(
            "Match (relative)",
            help="DISPLAY: relative = overall_score / max_overall_score per run (Option C). Raw value in next column.",
            min_value=0,
            max_value=1,
            format="%.2f",
        ),
        "Raw Match": st.column_config.NumberColumn(
            "Raw Match",
            help="Verbatim overall_score from pipeline (product: skill_component × similarity). Not scaled.",
            format="%.4f",
        ),
        "Similarity": st.column_config.NumberColumn(
            "Similarity",
            help="TF-IDF cosine raw (0–1), not a percentage.",
            format="%.4f",
        ),
    },
)

# --- candidate selection ---
# Use selectbox for robust click-equivalent (also supports dataframe selection pattern)
candidate_ids = [r["candidate_id"] for r in results]
# keep selected_id in sync
if st.session_state.get("selected_id") not in candidate_ids:
    st.session_state["selected_id"] = candidate_ids[0]

selected_id = st.selectbox(
    "Inspect candidate (click-equivalent)",
    candidate_ids,
    index=candidate_ids.index(st.session_state["selected_id"]),
    key="candidate_select",
)
st.session_state["selected_id"] = selected_id

selected = next((r for r in results if r["candidate_id"] == selected_id), None)
if selected is None:
    st.error("Selected candidate not found.")
    st.stop()

# ============================================================
# Candidate detail panel
# ============================================================
st.divider()
st.subheader(f"Candidate {selected['candidate_id']} — Rank #{selected['rank']}")

# Overall Match per display choice (Option C shows both)
rel_sel = relative_score(selected["overall_score"])
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Raw Match", f"{selected['overall_score']:.4f}", help="Verbatim overall_score from pipeline.")
with c2:
    st.metric("Relative Match", f"{rel_sel:.2%}", help="DISPLAY: relative = raw / max per run (Option C).")
    st.progress(rel_sel, text=f"Relative: {rel_sel:.0%} of top")
with c3:
    st.metric("Similarity (raw)", f"{selected['similarity']:.4f}", help="Raw TF-IDF cosine, not %.")

col_left, col_right = st.columns(2)
with col_left:
    st.markdown("**Matched skills ✓**")
    if selected["matched_skills"]:
        for s in selected["matched_skills"]:
            st.markdown(f"✓ {s}")
    else:
        st.caption("— none —")

with col_right:
    st.markdown("**Missing skills ✗**")
    if selected["missing_skills"]:
        for s in selected["missing_skills"]:
            st.markdown(f"✗ {s}")
    else:
        st.caption("— none —")

# Score breakdown — every component from score_breakdown dict
st.markdown("**Score breakdown**")
bd = selected.get("score_breakdown", {})
# Render all 9 keys per [P5] + guarantee every key present even if schema evolves
# Expected keys: matched_required, missing_required, matched_additional, total_required,
# total_additional, beta, skill_component, similarity_component, final_score
if bd:
    # Normalize display order
    ordered_keys = [
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
    # Show in two columns for readability
    bc1, bc2 = st.columns(2)
    with bc1:
        for k in ordered_keys[:5]:
            if k in bd:
                v = bd[k]
                if isinstance(v, list):
                    st.write(f"**{k}:** {', '.join(v) if v else '—'}")
                else:
                    st.write(f"**{k}:** {v}")
        # any extra keys not in ordered list
        for k, v in bd.items():
            if k not in ordered_keys:
                st.write(f"**{k}:** {v}")
    with bc2:
        for k in ordered_keys[5:]:
            if k in bd:
                v = bd[k]
                if isinstance(v, float):
                    st.write(f"**{k}:** {v:.4f}")
                else:
                    st.write(f"**{k}:** {v}")
    # also show as json for auditability
    with st.expander("Raw score_breakdown JSON"):
        st.json(bd)
else:
    st.caption("No breakdown available.")

# Explanation verbatim
st.markdown("**Why this candidate ranks here**")
st.info(selected.get("explanation", ""))

# Footer hint for screenshots
st.caption(
    "Screenshots for `outputs/screenshots/`: 1) Job input (sample+paste), 2) Resume upload/paste, "
    "3) Ranked table with relative bars, 4) Candidate detail (matched/missing + breakdown + explanation)."
)
