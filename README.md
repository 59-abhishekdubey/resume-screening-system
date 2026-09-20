# AI Resume Screening & Candidate Matching System

## 1. Project Overview
Evidence-first pipeline: JD + resumes (text or PDF) → ranked candidates with matched/missing skills, JD similarity, and deterministic explanation. `src/pipeline.py` is the sole orchestration entry point. Flask app in `app/app.py`; archived Streamlit copy in `app/app_streamlit.py`.

## 2. Problem Statement
Manual resume screening is slow and inconsistent. Keyword search misses variants (`sklearn` vs `Scikit-learn`); a single opaque score hides why a candidate ranked high or low. Need a reproducible system that extracts comparable skills and surfaces gaps.

## 3. Objective
Build a pipeline that cleans text [P1], extracts skills from a controlled vocabulary [P2], parses JDs into `JobProfile` [P3], measures TF-IDF similarity, scores with an explainable formula [P5], reports gaps [P6], handles PDFs [P8], and exposes results via a Flask dashboard with evaluation [P7].

## 4. Target Users
- Recruiters screening 20–200 resumes per role.
- Hiring managers who need to see why a candidate ranks where they do.
- Reviewers who need to clone, install, and reproduce results.

## 5. Dataset
- Source: `data/raw/Resume.csv` (Kaggle Resume dataset, CSV only; no native PDFs per [P8]).
- Size: **2484 rows, 24 categories** [P1] (verified by direct count of `data/raw/Resume.csv`; see `implementation .md` Phase 1 output).
- Columns: `ID`, `Resume_str`, `Resume_html`, `Category` [P1].
- Primary text field: `Resume_str` [P1] (`DECISIONS.md:1`).
- Available label: `Category` (distribution only; not hiring ground truth).
- Missing: direct JD labels, explicit skill labels, structured experience/education — excluded from scoring per [P1] sparsity (`DECISIONS.md:2,13`).

## 6. Dataset Analysis
Measured directly from `data/raw/Resume.csv` (verbatim, no rounding beyond full float):
- Rows 2484, categories 24. Counts: `ACCOUNTANT 118`, `ADVOCATE 118`, `AGRICULTURE 63`, `APPAREL 97`, `ARTS 103`, `AUTOMOBILE 36`, `AVIATION 117`, `BANKING 115`, `BPO 22`, `BUSINESS-DEVELOPMENT 120`, `CHEF 118`, `CONSTRUCTION 112`, `CONSULTANT 115`, `DESIGNER 107`, `DIGITAL-MEDIA 96`, `ENGINEERING 118`, `FINANCE 118`, `FITNESS 117`, `HEALTHCARE 115`, `HR 110`, `INFORMATION-TECHNOLOGY 120`, `PUBLIC-RELATIONS 111`, `SALES 116`, `TEACHER 102`.
- Missing values: `ID 0`, `Resume_str 0`, `Resume_html 0`, `Category 0`; plus 1 empty `Resume_str`, 0 empty `Resume_html`.
- Duplicates: 0 duplicate IDs (2484 unique), 2 duplicate `Resume_str` texts (2482 unique).
- Characters: mean `6295.3087761674715`, std `2769.251458139663`, min `21.0`, 25% `5160.0`, median `5886.5`, 75% `7227.25`, max `38842.0`.
- Words: mean `811.3256843800322`, std `371.0069064804546`, min `0.0`, 25% `651.0`, median `757.0`, 75% `933.0`, max `5190.0`.
- Text contains HTML artifacts, URLs, emails, phones, bullets, inconsistent spacing — drives cleaning in `src/preprocessing.py` [P1] (`DECISIONS.md:3`).

## 7. System Architecture
[P9] flow `clean_text → tfidf_similarity → score_candidate → sort → build_candidate_result`:
```
JD (dict/JobProfile) → parse_job() [P3] → JobProfile
Resume PDF/Text → extract_text_from_pdf [P8] → clean_text() [P1] → tfidf_similarity [P4] → score_candidate() [P5] → sort (-final_score, candidate_id) → build_candidate_result() [P9]
```
Result dict has 8 keys [P9]: `rank, candidate_id, overall_score, matched_skills, missing_skills, similarity, score_breakdown(9 keys), explanation`. Exposed via `screen_resumes`, `screen_from_pdf_folder`, `save_screening_report` in `src/pipeline.py`.

## 8. NLP Pipeline
- `clean_text()` strips URLs, emails, phones per [P1]; normalizes whitespace; no lowercasing (`TEXT_CLEANING_OPTS` in `src/config.py`).
- Same cleaning for resumes and JDs before extraction and TF-IDF.
- Flow per [P9]: `clean_text → tfidf_similarity → score_candidate → sort → build_candidate_result`.

## 9. Skill Extraction
- Vocabulary `SKILL_VOCABULARY` (42 canonical) and `SKILL_ALIASES` in `src/config.py` [P2].
- `extract_skills()` uses word-boundary regex + alias lookup; deduplicated by first appearance.
- Extracted skills are reconciled with JD-declared lists in `src/job_parser.py`.

## 10. Job Description Parsing
- `JobProfile` dataclass with `required_skills`/`optional_skills` [P3].
- `_normalize_job()` accepts raw dict, JobProfile-like dict, or `JobProfile`.
- Samples in `data/raw/sample_jobs.json` (11 roles; e.g., ML Engineer required `["Python","scikit-learn","Docker","Kubernetes","SQL"]`).

## 11. Similarity Method
- **TF-IDF cosine** is the pipeline method. `tfidf_similarity()` fits `TfidfVectorizer` on `[resume_text, jd_text]` per call; returns `0.0` if empty. Displayed as a percentage (0–1 mapped to 0–100%).
- Semantic (`sentence-transformers/all-MiniLM-L6-v2`) was evaluated in `notebooks/phase4_similarity_compare.py` and `outputs/results/similarity_experiment.csv` (250 rows) but is not used in `screen_resumes` [P9].

## 12. Scoring Method
Formula 3 — Expanded-Skill-Weighted (ESW) [P5]:
```
skill_component = (matched_required + β·matched_additional) / (total_required + β·total_additional), β=0.5
similarity_component = tfidf_similarity ∈ [0,1]
final_score = skill_component × similarity_component  (multiplicative [P9])
```
`score_candidate()` returns 9 keys [P5]: `matched_required, missing_required, matched_additional, total_required, total_additional, beta, skill_component, similarity_component, final_score`. The dashboard surfaces skill coverage and JD similarity as separate recruiter-facing signals. Internal composite scores are not shown to avoid implying an absolute fit percentage.

## 13. Candidate Ranking
Sorted by `(-final_score, candidate_id)` for determinism [P9]. CSV-vs-PDF parity verified: identical rankings, max delta `0.0022`, re-run sha256 match.

## 14. Skill Gap Analysis
`src/skill_gap.py` [P6]: `compute_gap()` returns sorted `matched`/`missing`; `coverage_ratio()` handles empty required. Pipeline uses `score_candidate` as sole entry point for extraction and gap.

## 15. Explainability
Deterministic template in `src/pipeline.py:generate_explanation()` [P6]:
1. `coverage_ratio >=0.8` → "Strong required-skill coverage"
2. `similarity >=0.6` → "High similarity to job description"
3. `similarity >=0.35` → "Moderate similarity to job description"
4. `missing` non-empty → "Missing: {sorted missing}"
5. Otherwise → "Insufficient signal to explain ranking"
Joined by `"; "`. Example: `10089434` → "Moderate similarity to job description; Missing: Docker, Kubernetes, Python, Scikit-learn".

## 16. Evaluation
Figures trace to `outputs/results/` files.

**Skill extraction — `skill_eval.csv` (via `evaluation/evaluate_skills.py`):**
| skill | evaluations | precision | recall | F1 |
|---|---|---|---|---|
| Docker | 1 | 1.0 | 1.0 | 1.0 |
| Git | 5 | 0.8 | 0.8 | 0.8 |
| Java | 9 | 0.7778 | 0.7778 | 0.7778 |
| JavaScript | 8 | 0.75 | 0.75 | 0.75 |
| Python | 10 | 0.8 | 0.8 | 0.8 |
| SQL | 7 | 0.8571 | 0.8571 | 0.8571 |
| MICRO |  | 0.8 | 0.8 | 0.8 |
| MACRO |  | 0.8308 | 0.8308 | 0.8308 |

**Ranking — `ranking_eval.csv` (via `labeling_template.csv` + `similarity_experiment.csv`):**
All 5 pairs score `0.0` for every K (P@1..P@10, R@1..R@10). Source `ranking_eval.csv:2-6`. NDCG/MAP not measured.

## 17. Error Analysis
`outputs/results/error_cases.csv` contains header only (0 data rows). Unlogged modes observed via inspection:
- Vocabulary miss — alias or word-boundary gap for novel phrasing.
- TF-IDF lexical gap — paraphrase lowers cosine despite semantic relevance.
- Sparse product — low `skill_component` drives `final_score` near 0 even when `similarity` is moderate.
Populate via `evaluation/error_analysis.py`.

## 18. Demo
**Current Flask UI** (`app/app.py` + `app/templates/*.html`):

- **Job input:** sample role dropdown plus "Paste custom JD" toggle; optional role label override.
- **Resume input:** multi-PDF upload (`data/raw/pdfs/*.pdf` fixtures) plus "Paste single resume text" toggle with candidate ID.
- **Results table (`/results`):** columns Rank, Candidate, Match Summary, Skill Coverage, JD Similarity, Missing Skills, Action. Each row links to candidate detail.
- **Candidate detail (`/candidate/<id>`):** Match Summary banner, Skill Match (matched/missing lists), Skill Coverage (X / Y), JD Similarity (%), and Why-this-result explanation with 9-key breakdown.

Screenshots: `outputs/screenshots/` is empty on 2026-09-20 — capture pending. Save captures as `outputs/screenshots/01_index.png`, `02_results.png`, `03_candidate.png` with relative paths. Tracked figures:
![Category distribution](outputs/figures/category_distribution.png)
![Resume length distribution](outputs/figures/resume_length_distribution.png)
![Similarity distribution](outputs/figures/similarity_distribution.png)

## 19. Limitations
1. PDF fixtures are generated, not real — 20 rendered via `notebooks/phase8_generate_fixtures.py` (Helvetica), gitignored; no OCR for scanned resumes.
2. `Category` ≠ hiring ground truth — small synthetic relevance judgments.
3. Small ground-truth sample — 6 skills and 5 ranking pairs only.
4. No OCR, layout-aware extraction, or experience/education parsing by design [P1][P8].
5. Vocabulary limited to 42 canonical skills; aliases must be curated.
6. The dashboard intentionally does not show a single composite score, because the pipeline's multiplicative formula produces values that are not intuitive as percentages.

## 20. Future Improvements
- Curate ≥50 adjudicated judgments; measure NDCG alongside P@K/R@K.
- Expand vocabulary and learn aliases from data; improve multi-word handling.
- Offer semantic similarity as optional method with caching.
- Replace synthetic PDFs with diverse real resumes; add OCR fallback.
- Add feature-flagged experience/education extraction.

## 21. Installation
Windows + `cmd.exe`, Python 3.14:
```cmd
git clone <your-fork-url>
cd resume-screening-system
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -c "import pdfplumber; print(pdfplumber.__version__)"
```
`requirements.txt`: `Flask>=3.0`, `pdfplumber>=0.11.0`, `pdfminer.six>=20221105`, `pypdfium2>=4.0.0`.

## 22. Usage
From repo root, venv activated:
```cmd
:: tests
pytest -q
:: dashboard (Flask)
python app/app.py
:: then open http://127.0.0.1:5000
:: fixtures (only if regenerating PDFs)
python notebooks\phase8_generate_fixtures.py
:: evaluation
python evaluation\evaluate_skills.py
python evaluation\evaluate_ranking.py
```
Flow: select job or paste JD → upload PDFs or paste resume → Run Screening → results table → candidate detail.

## 23. Project Structure
```
resume-screening-system/
├── DECISIONS.md
├── README.md
├── requirements.txt
├── app/
│   ├── app.py
│   ├── app_streamlit.py          # archived
│   ├── templates/
│   │   ├── index.html
│   │   ├── result.html
│   │   └── candidate.html
│   └── static/
│       └── style.css
├── data/raw/
│   ├── Resume.csv
│   ├── sample_jobs.json
│   └── pdfs/                     # gitignored fixtures
├── src/
│   ├── config.py
│   ├── preprocessing.py
│   ├── skill_extraction.py
│   ├── job_parser.py
│   ├── similarity.py
│   ├── scoring.py
│   ├── skill_gap.py
│   ├── pdf_parser.py
│   └── pipeline.py
├── evaluation/
├── tests/
└── outputs/
    ├── figures/
    ├── results/
    └── screenshots/               # capture pending
```
49 tracked files — regenerate with: `git ls-files | find /c /v ""` (Windows) or `git ls-files | wc -l`.

