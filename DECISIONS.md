[P1] Primary text field: Resume_str
[P1] Skip Experience & Education features — data too sparse
[P1] Strip emails/phones/URLs during cleaning
[P2] Skill vocabulary in src/config.py, canonical names
[P3] JobProfile is a dataclass; required/optional skills are canonical
[P4] Similarity signal from Phase 4 — I will select tfidf or semantic at call time
[P5] CHOSEN FORMULA: Formula 3 — Expanded-Skill-Weighted (ESW)
         score = (matched_required + β·matched_additional) / (total_required + β·total_additional)
                 × similarity_score
         β = module-level tunable, default 0.5 default; tunable via WEIGHTS dict in src/scoring.py
[P5] score_candidate returns 9-key breakdown dict (matched_required, missing_required, matched_additional, total_required, total_additional, beta, skill_component, similarity_component, final_score)
[P5] rank_candidates() defaults to TF-IDF similarity; semantic available via method="semantic"
[P5] Experience/Education excluded from scoring per [P1] sparsity
[P5] Score range [0,1], displayed as percentage in UI











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

## Phase 8 — PDF Resume Pipeline
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