# DECISIONS

Audit trail for the AI Resume Screening project. Each [PN] entry records a decision made during Phase N. Entries are append-only; superseded decisions are corrected at the bottom, never edited in place.

_Last updated: 2026-09-20_

## Phase 1 — Dataset Reconnaissance
[P1] Primary text field: Resume_str
[P1] Skip Experience & Education features — data too sparse
[P1] Strip emails/phones/URLs during cleaning

## Phase 2 — Preprocessing & Skill Extraction
[P2] Skill vocabulary in src/config.py, canonical names

## Phase 3 — Job Description Parsing
[P3] JobProfile is a dataclass; required/optional skills are canonical

## Phase 4 — Resume ↔ JD Similarity
[P4] Similarity signal from Phase 4 — I will select tfidf or semantic at call time

## Phase 5 — Candidate Scoring & Ranking
[P5] CHOSEN FORMULA: Formula 3 — Expanded-Skill-Weighted (ESW)
     score = (matched_required + β·matched_additional) / (total_required + β·total_additional)
             × similarity_score
     β = module-level tunable, default 0.5 default; tunable via WEIGHTS dict in src/scoring.py
[P5] score_candidate returns 9-key breakdown dict (matched_required, missing_required, matched_additional, total_required, total_additional, beta, skill_component, similarity_component, final_score)
[P5] rank_candidates() defaults to TF-IDF similarity; semantic available via method="semantic"
[P5] Experience/Education excluded from scoring per [P1] sparsity
[P5] Score range [0,1], displayed as percentage in UI

## Phase 6 — Skill Gap & Explainability

[p6]:

Both files are implemented and verified. Here's a summary:
src/skill_gap.py
- compute_gap(candidate_skills, required_skills) — returns {"matched": sorted intersect, "missing": sorted required - candidate}. Handles duplicates via set dedup.
- coverage_ratio(matched, required) — returns len(matched)/len(required), safely returns 0.0 when required is empty.
src/pipeline.py
- build_candidate_result(...) — composes the user-facing dict from a candidate ID, profile, job profile, similarity score, and score dict (from scoring.py). Uses score_dict["matched_required"] as matched_skills, etc.
- generate_explanation(result) — deterministic templating per the 5 rules:
1. coverage_ratio(matched, matched+missing) >= 0.8 → "Strong required-skill coverage"
2. similarity >= 0.6 → "High similarity to job description" (elif #3 is mutually exclusive)
3. similarity >= 0.35 → "Moderate similarity to job description"
4. missing_skills non-empty → "Missing: " + ", ".join(sorted(missing_skills))
5. If no parts matched → fallback "Insufficient signal to explain ranking"
- Parts joined with "; "; running twice on same input gives identical output.
All self-checks pass, no forbidden imports, and the files only contain presentation-layer code per the Phase 6 constraints.

## Phase 7 — Evaluation & Error Analysis
[P7] NOT RECORDED — decisions from this phase were not captured in real time. Backfill by inspecting outputs/results/ and git log if needed.

## Phase 8 — PDF Pipeline
[P8] Kaggle Resume dataset ships as CSV only. Real PDFs unavailable.
[P8] Phase 8 validated against 20 fixture PDFs generated from Resume_str
     → data/raw/pdfs/<ID>.pdf (single-column Helvetica, multi-page wrap)
[P8] Library: pdfplumber (chosen over pypdf/PyMuPDF for layout tolerance)
[P8] Encryption detection via pdf.is_encrypted + exception catch
     (not %PDF- text sniffing — that was a bug, now fixed)
[P8] Runtime deps: pdfplumber, pdfminer.six, pypdfium2
[P8] Dev-only dep: reportlab (fixture generation only — not imported in src/)
[P8] pdf_parser NOT wired into pipeline.py — Phase 9 owns orchestration
[P8] Empty-text extraction returns "" (never raises) except FileNotFoundError

## Phase 9 — End-to-End Pipeline
[P9] pipeline.py exposes: screen_resumes, screen_from_pdf_folder, save_screening_report
[P9] Flow: clean_text → tfidf_similarity → score_candidate → sort → build_candidate_result
[P9] score_candidate is the SOLE entry point for skill extraction + gap — no duplication
[P9] Result dict has exactly 8 keys: rank, candidate_id, overall_score, matched_skills,
     missing_skills, similarity, score_breakdown, explanation
[P9] build_candidate_result signature: (candidate_id, job_profile, similarity_score, score_dict)
[P9] Tie-break rule: sort by (-final_score, candidate_id) for determinism
[P9] CSV-vs-PDF parity verified: identical rankings, max score delta 0.0022,
     skill-diff count 0, bit-identical on re-run (sha256 match)
[P9] Repo not git-initialized — file-modification checks done via timestamps + SHA256
[P9] Score formula is MULTIPLICATIVE: final = skill_component × similarity_component.
     Top candidate currently scores 0.055 (5.5%). Display handling deferred to Phase 10.

## Phase 10 — Streamlit UI
[P10] NOT RECORDED — decisions from this phase were not captured in real time. Backfill by inspecting outputs/results/ and git log if needed.

## Phase 10b — Flask Migration
[P10b] Framework switched from Streamlit to Flask for portfolio impression.
[P10b] app/app_streamlit.py archived (byte-copy of Phase 10 app.py) — rollback path.
[P10b] Flask app is single-file, session-only (no DB, no auth, no extensions).
[P10b] Routes: /, /screen (POST), /results, /candidate/<id>.
[P10b] Calls pipeline.screen_resumes and pipeline.screen_from_pdf_folder only.
[P10b] Relative Match display (raw / max) preserved from [P10] — LOCKED.
[P10b] sample_jobs.json expanded to 11 roles (was: 5).
[P10b] README sections 12, 18, 21, 22, 23 updated.
[P10b] Zero changes to src/, tests/, evaluation/.

## Phase 10c — Human-Readable Verdicts
[P10c] Added verdict layer (Strong/Good/Partial/Weak Match) on Flask UI.
[P10c] Primary signal: required-skill coverage ratio. Secondary: relative match.
     Similarity shown as supporting evidence only.
[P10c] Thresholds exposed as constants in app/app.py; tunable per batch.
[P10c] Reasoning is deterministic template string — NO LLM.
[P10c] Raw scores, similarity, 9-key breakdown all PRESERVED below verdict.
[P10c] Zero changes to src/, tests/, evaluation/.

## Phase 10d — Missing Skills in Results Table
[P10d] Missing skills surfaced under Verdict cell (sub-line, not new column).
[P10d] Display cap = MISSING_DISPLAY_CAP (4) — longer lists show "+N more".
[P10d] Empty missing_skills renders no line (no "Missing: none" noise).
[P10d] Zero changes to src/, tests/, evaluation/.
[P10d] This is the final UI change — project ships after this.

## Phase 10e — Recruiter-Grade UI Polish
[P10e] Header cleaned — removed "from src/pipeline.py" and dev language.
[P10e] Index: "Job Details" + "Upload Resumes" sections; button "Screen Candidates".
[P10e] Results columns: Rank, Candidate, Match Summary, Skill Coverage, JD Similarity, Action. REMOVED: Relative Match, Raw Score, max caption.
[P10e] Match Summary labels softened (Strong/Good/Partial/Limited skill overlap).
[P10e] Candidate detail restructured with Why-this-result bullets.
[P10e] Added screening-assistance footer to index + results.
[P10e] Skill Coverage = matched_required / total_required from score_breakdown.
[P10e] JD Similarity = round(similarity * 100, 1) + "%".
[P10e] Zero changes to src/, tests/, evaluation/, pipeline behavior.

## Phase 11 — Testing
[P11] NOT RECORDED — decisions from this phase were not captured in real time. Backfill by inspecting outputs/results/ and git log if needed.

## Phase 12 — README (Portfolio Docs)
[P12] NOT RECORDED — decisions from this phase were not captured in real time. Backfill by inspecting outputs/results/ and git log if needed.

## Phase 12b — README Alignment
[P12b] README updated to match current UI (Match Summary, Skill Coverage, JD Similarity, Missing Skills — no raw score, no relative bars).
[P12b] 23-section structure preserved.
[P12b] Sections 5 and 6 kept verbatim (numeric ground truth from [P1]).
[P12b] New limitation added: composite score intentionally hidden from UI.
[P12b] Zero changes to src/, tests/, evaluation/, app/.

## Phase 12c — DECISIONS.md Polish
[P12c] NOT RECORDED — decisions from this phase were not captured in real time. Backfill by inspecting outputs/results/ and git log if needed.

## Corrections & Supersessions
Entries here correct or supersede earlier [PN] lines without editing history. Cross-reference the affected [PN].

- [P9] "Repo not git-initialized" is SUPERSEDED. The repo was initialized and committed during Phase 10b. Git history: commits c226d4f → 1632332 → … (see `git log`). This line remains in the [P9] block as a historical record of state at Phase 9 time.
