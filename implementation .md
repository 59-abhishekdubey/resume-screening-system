# AI Resume Screening & Candidate Matching System

## Detailed Implementation Plan

---

# Overall Development Flow

```text
PHASE 1
Dataset Reconnaissance
        ↓
PHASE 2
Baseline Resume + Skill Pipeline
        ↓
PHASE 3
Job Description Processing
        ↓
PHASE 4
Resume ↔ Job Similarity
        ↓
PHASE 5
Candidate Scoring & Ranking
        ↓
PHASE 6
Skill Gap Analysis + Explainability
        ↓
PHASE 7
Evaluation & Error Analysis
        ↓
PHASE 8
PDF Resume Pipeline
        ↓
PHASE 9
Final Recruiter Application
        ↓
PHASE 10
Testing + Documentation + Portfolio
```

The phases are deliberately sequential.

**Do not jump to the dashboard before the underlying screening logic is validated.**

---

# PHASE 1 — Dataset Reconnaissance

## Goal

Understand what the dataset actually contains before deciding what the final system can reliably do.

This phase answers:

> "What information do we have, and what can we realistically extract from it?"

---

## What you will do

### 1. Load the dataset

Start with the existing `Resume.csv`.

Understand:

* number of records
* number of columns
* data types
* unique categories
* resume text availability
* missing values

---

### 2. Understand the dataset structure

Document the meaning of:

```text
ID
Resume_str
Resume_html
Category
```

Determine which fields will actually be used.

For the screening system, `Resume_str` will probably be the primary experimental input.

---

### 3. Analyze job categories

Investigate:

```text
Number of categories
Resumes per category
Class imbalance
```

Visualize the distribution.

This is important because the category distribution affects how we design experiments.

---

### 4. Inspect resume text

Look at actual examples.

Check for:

* formatting noise
* HTML artifacts
* unusual characters
* repeated sections
* inconsistent spacing
* bullet characters
* URLs
* email addresses
* phone numbers
* section headings
* capitalization
* skill variations

Do not decide preprocessing rules before looking at the actual text.

---

### 5. Analyze resume length

Investigate:

```text
characters
words
tokens
```

This helps identify extremely short or suspicious records.

---

### 6. Check duplicates

Determine whether:

* identical resumes exist
* near-duplicate resumes exist
* the same candidate appears more than once

This becomes especially important during evaluation.

---

### 7. Investigate skills

Sample resumes from different categories and manually inspect common skills.

Create an initial skill vocabulary from observed data rather than blindly using a huge predefined list.

---

### 8. Investigate experience and education

This is particularly important because your original PRD proposed:

```text
20% Experience
10% Education
```

We need to determine:

* Are education sections consistently present?
* Are degree names recognizable?
* Are years of experience explicitly stated?
* Are dates structured consistently?
* Can these fields be extracted with reasonable reliability?

If not, we should **not force these features into the final scoring formula.**

---

## Files changed

### `notebooks/Resume_Screening_System_(1).ipynb`

**Main file changed.**

Add the complete dataset exploration here.

### `data/raw/`

**No modification.**

Keep the original dataset untouched.

### `outputs/figures/`

May receive:

```text
category_distribution.png
resume_length_distribution.png
```

### `README.md`

**Do not fully write it yet.**

Only update later with confirmed dataset information.

---

## Phase 1 output

You should finish with a short conclusion:

```text
Dataset:
2,484 resumes
24 categories

Primary text field:
Resume_str

Available label:
Category

Missing:
Direct JD labels
Explicit skill labels
Structured experience
Structured education
```

The exact findings should come from your analysis.

---

# PHASE 2 — Baseline Resume Processing & Skill Extraction

## Goal

Build the simplest reliable version of:

```text
Resume
 ↓
Clean text
 ↓
Extract skills
```

Before using advanced NLP.

---

# Step 2.1 — Text preprocessing

### File

`src/preprocessing.py`

Implement reusable cleaning functions.

Example responsibilities:

```text
clean_text()
normalize_whitespace()
remove_unnecessary_characters()
```

The exact operations should be based on Phase 1 findings.

### Notebook

`notebooks/Resume_Screening_System_(1).ipynb`

First experiment with the cleaning rules here.

Only move the validated version into `src/preprocessing.py`.

---

# Step 2.2 — Build initial skill dictionary

### File

`src/skill_extraction.py`

Create an initial controlled vocabulary.

For example:

```text
Python
Java
SQL
Machine Learning
Pandas
NumPy
Scikit-learn
TensorFlow
PyTorch
Git
Docker
AWS
Azure
```

But the final dictionary should be informed by the dataset and project roles.

---

# Step 2.3 — Skill matching baseline

Start simple.

```text
Resume
 ↓
Normalized text
 ↓
Skill dictionary
 ↓
Pattern matching
 ↓
Detected skills
```

Do not immediately use complex NER.

We need a baseline first.

---

# Step 2.4 — Skill normalization

Add mappings such as:

```text
sklearn
scikit learn
scikit-learn

        ↓

Scikit-learn
```

Similarly investigate other variations.

---

## Files changed

```text
notebooks/Resume_Screening_System_(1).ipynb
src/preprocessing.py
src/skill_extraction.py
src/config.py
```

`config.py` can eventually contain the skill dictionary and normalization mappings.

---

## Phase 2 output

For each resume we should be able to produce:

```text
Candidate ID
Category
Cleaned Resume
Detected Skills
```

Example:

```text
Candidate: 1024

Skills:
Python
Pandas
NumPy
SQL
Scikit-learn
Git
```

---

# PHASE 3 — Job Description Processing

## Goal

Turn an unstructured job description into a structured job profile.

---

## Step 3.1 — Create controlled job descriptions

### File

`data/job_descriptions/sample_jobs.json`

Create several test roles.

For example:

```text
Machine Learning Engineer
Data Analyst
Python Developer
```

Each should contain:

```text
role
description
required_skills
optional_skills
```

The descriptions should resemble realistic job descriptions but remain controlled enough for experimentation.

---

## Step 3.2 — Job description preprocessing

### File

`src/job_parser.py`

Process the job description using the same general text-cleaning principles used for resumes.

---

## Step 3.3 — Extract job skills

Use the same skill extraction and normalization system.

```text
Job Description
       ↓
Clean
       ↓
Extract skills
       ↓
Normalize skills
       ↓
Job Profile
```

This ensures that:

```text
Resume skill extraction
```

and

```text
Job skill extraction
```

speak the same vocabulary.

---

## Files changed

```text
data/job_descriptions/sample_jobs.json
src/job_parser.py
src/skill_extraction.py
notebooks/Resume_Screening_System_(1).ipynb
```

---

## Phase 3 output

Example:

```text
Machine Learning Engineer

Required:
Python
Machine Learning
Pandas
NumPy
Scikit-learn
SQL
Git

Optional:
Docker
AWS
```

---

# PHASE 4 — Resume-to-Role Similarity

## Goal

Measure how similar a resume is to a job description.

This is where the ML component becomes more meaningful.

---

# Step 4.1 — TF-IDF baseline

### File

`src/similarity.py`

Implement:

```text
Resume + Job Description
          ↓
        TF-IDF
          ↓
Vector representation
          ↓
Cosine similarity
```

The output:

```text
0 → very different
1 → highly similar
```

Treat this as a similarity signal, not a hiring score.

---

# Step 4.2 — Compare with your existing semantic experiment

Your current notebook already experimented with:

```text
SentenceTransformer
        ↓
Embeddings
        ↓
Cosine similarity
```

Do not discard that work.

Use the notebook to compare:

```text
TF-IDF
vs
SentenceTransformer
```

on the same controlled examples.

---

# Step 4.3 — Analyze the results

Investigate cases where:

```text
TF-IDF says high similarity
but semantic model says low similarity
```

and vice versa.

This is more valuable than simply selecting the more advanced model.

---

## Files changed

```text
notebooks/Resume_Screening_System_(1).ipynb
src/similarity.py
src/config.py
```

Potential output:

```text
outputs/results/similarity_experiment.csv
outputs/figures/similarity_distribution.png
```

---

## Phase 4 output

A validated similarity component:

```text
Candidate A → 0.84
Candidate B → 0.71
Candidate C → 0.53
```

plus an explanation of why the chosen similarity method was selected.

---

# PHASE 5 — Candidate Scoring & Ranking

## Goal

Combine the matching signals into an explainable candidate score.

---

# Step 5.1 — Required skill match

Calculate:

```text
matched required skills
-----------------------
total required skills
```

For example:

```text
6 required skills
5 matched

5 / 6 = 83.3%
```

---

# Step 5.2 — Additional skill match

Identify useful skills present in the resume but not explicitly required.

This can become a separate signal.

Example:

```text
Required:
Python
SQL
Pandas

Candidate:
Python
SQL
Pandas
Docker
AWS
Git
```

Additional:

```text
Docker
AWS
Git
```

---

# Step 5.3 — Decide whether experience and education belong

Return to the findings from Phase 1.

If the data supports reliable extraction:

```text
Experience
Education
```

can be evaluated.

If not:

**leave them out rather than inventing precision.**

This is an important project-design decision.

---

# Step 5.4 — Design the scoring formula

### File

`src/scoring.py`

Start with a simple, explainable formula.

For example:

```text
Final Score =
Skill Match × weight
+
Similarity × weight
+
Additional Skills × weight
```

The exact weights must be selected through experimentation.

Do not simply copy the original 40/25/20/10/5 proposal.

---

# Step 5.5 — Candidate ranking

### File

`src/ranking.py`

Sort candidates:

```text
score descending
```

Return:

```text
Rank
Candidate
Overall Score
Matched Skills
Missing Skills
Similarity
```

---

## Files changed

```text
src/scoring.py
src/ranking.py
src/config.py
notebooks/Resume_Screening_System_(1).ipynb
```

Potential output:

```text
outputs/results/candidate_rankings.csv
```

---

# PHASE 6 — Skill Gap Analysis & Explainability

## Goal

Answer the recruiter's most important follow-up question:

> "Why did this candidate receive this score?"

---

# Step 6.1 — Skill gap calculation

### File

`src/skill_gap.py`

Logic:

```text
Required Skills
      -
Candidate Skills
      =
Missing Skills
```

Return both:

```text
Matched Skills
Missing Skills
```

---

# Step 6.2 — Score breakdown

The candidate result should expose the components.

Example:

```text
Candidate A

Required Skill Match       36 / 40
JD Similarity              21 / 25
Additional Skills           4 / 5
----------------------------------
Overall Score              61 / 70
```

The actual components and weights will depend on Phase 5.

---

# Step 6.3 — Generate ranking explanation

Create a deterministic explanation based on measurable results.

For example:

```text
Strong required-skill coverage
High similarity with the job description
Missing Docker and AWS
```

Avoid vague statements that aren't supported by the underlying measurements.

---

## Files changed

```text
src/skill_gap.py
src/scoring.py
src/ranking.py
src/pipeline.py
```

---

## Phase 6 output

Each candidate gets:

```text
Overall Score
Matched Skills
Missing Skills
Similarity Score
Score Breakdown
Ranking Explanation
```

This becomes the core explainability layer of the product.

---

# PHASE 7 — Evaluation & Error Analysis

## Goal

Determine whether the system actually works.

This phase is essential.

A ranking table alone is not evaluation.

---

# Step 7.1 — Skill extraction evaluation

### File

`evaluation/evaluate_skills.py`

Create a manually verified sample.

Compare:

```text
Expected Skills
vs
Predicted Skills
```

Calculate where appropriate:

```text
Precision
Recall
F1
```

Investigate missed skills and false detections.

---

# Step 7.2 — Similarity evaluation

### Notebook

`notebooks/Resume_Screening_System_(1).ipynb`

Test controlled examples:

```text
Relevant Resume + Relevant JD
Relevant Resume + Unrelated JD
```

Analyze score distributions.

The dataset's `Category` can assist with controlled experiments, but category should not be treated as a perfect hiring ground truth.

---

# Step 7.3 — Ranking evaluation

### File

`evaluation/evaluate_ranking.py`

Create manually reviewed relevance judgments for a controlled set of job descriptions.

Investigate:

```text
Top-5 relevance
Precision@K
Recall@K
```

Potentially:

```text
NDCG@K
```

only if it adds useful value.

Don't add metrics just to make the project look sophisticated.

---

# Step 7.4 — Error analysis

### File

`evaluation/error_analysis.py`

Record important failure cases.

Example:

```text
Resume:
Strong ML experience

System:
Low similarity

Reason:
Resume wording differs significantly from JD wording.
```

Or:

```text
Resume:
"worked with sklearn"

System:
Missing Scikit-learn

Reason:
Normalization rule missing.
```

This tells us what should actually be improved.

---

## Files changed

```text
evaluation/evaluate_skills.py
evaluation/evaluate_ranking.py
evaluation/error_analysis.py
notebooks/Resume_Screening_System_(1).ipynb
outputs/results/
outputs/figures/
```

---

# PHASE 8 — PDF Resume Pipeline

## Goal

Move from:

```text
CSV → screening
```

to:

```text
PDF → extraction → screening
```

This makes the project much closer to the actual recruiter use case.

---

# Step 8.1 — PDF extraction

### File

`src/pdf_parser.py`

Implement:

```text
PDF
 ↓
Text extraction
 ↓
Raw text
```

Use an appropriate Python PDF extraction library.

---

# Step 8.2 — Connect PDF extraction to preprocessing

```text
PDF
 ↓
pdf_parser.py
 ↓
preprocessing.py
 ↓
skill_extraction.py
```

The rest of the pipeline should not care whether the original input was:

```text
CSV text
```

or:

```text
PDF
```

---

# Step 8.3 — Test with dataset PDFs

Use some of the original PDF resumes in the dataset.

Compare:

```text
Extracted PDF text
vs
Resume_str
```

Look for extraction failures.

---

## Files changed

```text
src/pdf_parser.py
src/pipeline.py
notebooks/Resume_Screening_System_(1).ipynb
```

Potential test files:

```text
tests/test_pdf_parser.py
```

---

# PHASE 9 — End-to-End Pipeline

## Goal

Connect everything into one reusable pipeline.

### Main file

`src/pipeline.py`

The pipeline becomes:

```text
Job Description
       ↓
Job Parser
       ↓
Job Profile
       │
       │
       ↓
Resume PDF/Text
       ↓
Text Extraction
       ↓
Preprocessing
       ↓
Skill Extraction
       ↓
Skill Normalization
       ↓
Resume Profile
       ↓
Similarity
       ↓
Skill Matching
       ↓
Scoring
       ↓
Ranking
       ↓
Skill Gap Analysis
       ↓
Explainable Result
```

The pipeline should call the individual modules.

It should **not duplicate their logic**.

---

## Files changed

```text
src/pipeline.py
src/preprocessing.py
src/pdf_parser.py
src/job_parser.py
src/skill_extraction.py
src/similarity.py
src/scoring.py
src/ranking.py
src/skill_gap.py
```

At this stage, the individual modules should be relatively stable.

---

# PHASE 10 — Recruiter Application

## Goal

Turn the validated ML pipeline into a usable demo.

### File

`app/app.py`

The interface should allow:

```text
1. Enter/select job role
2. Enter/paste job description
3. Upload resumes
4. Run screening
5. View ranked candidates
6. Inspect individual candidate
```

---

## Main dashboard

Show:

```text
AI CANDIDATE SCREENING

Role:
Machine Learning Engineer

Candidates:
25
```

Then:

```text
Rank | Candidate | Match
-------------------------
#1   | Candidate A | 91%
#2   | Candidate F | 87%
#3   | Candidate C | 82%
```

---

## Candidate detail

Selecting a candidate should display:

```text
Overall Match

Matched Skills
✓ Python
✓ Pandas
✓ NumPy
✓ SQL
✓ Git

Missing Skills
✗ Docker
✗ AWS

Similarity
82%

Score Breakdown
...

Why this candidate ranks here
...
```

The UI should expose the underlying evidence instead of hiding everything behind a single score.

---

## Optional visual comparison

If useful:

```text
Candidate A
Candidate B
Candidate C
```

could be compared using:

* skill coverage
* similarity
* overall score
* missing skills

This directly addresses the internship's optional visual-comparison feature.

---

## Files changed

```text
app/app.py
outputs/screenshots/
```

Potentially:

```text
app/components/
```

but **only if the application becomes large enough to justify it.**

Don't create unnecessary frontend architecture.

---

# PHASE 11 — Testing

## Goal

Make sure changes don't break previously validated functionality.

---

### `tests/test_preprocessing.py`

Test:

```text
Cleaning
Whitespace normalization
Empty input handling
```

---

### `tests/test_skill_extraction.py`

Test:

```text
Skill detection
Skill normalization
Synonyms
Missing skills
```

---

### `tests/test_similarity.py`

Test:

```text
Similarity calculation
Identical text
Different text
Empty input
```

---

### `tests/test_scoring.py`

Test:

```text
Score calculation
Weight changes
Boundary cases
```

---

### Optional

`tests/test_pdf_parser.py`

Test PDF extraction with sample resumes.

---

# PHASE 12 — Documentation & Portfolio

## Goal

Turn the technical project into a project that another person can understand and reproduce.

---

# README.md

Document:

```text
1. Project Overview
2. Problem Statement
3. Objective
4. Target Users
5. Dataset
6. Dataset Analysis
7. System Architecture
8. NLP Pipeline
9. Skill Extraction
10. Job Description Parsing
11. Similarity Method
12. Scoring Method
13. Candidate Ranking
14. Skill Gap Analysis
15. Explainability
16. Evaluation
17. Error Analysis
18. Demo
19. Limitations
20. Future Improvements
21. Installation
22. Usage
23. Project Structure
```

---

# Architecture diagram

Show:

```text
JD
 ↓
JD Parser
 ↓
Job Profile
 ↓
Matching Engine ← Resume Pipeline
 ↓
Scoring
 ↓
Ranking
 ↓
Skill Gaps
 ↓
Dashboard
```

---

# Screenshots

Store in:

```text
outputs/screenshots/
```

Capture:

1. Job description input
2. Candidate ranking
3. Candidate detail
4. Skill gaps
5. Score explanation
6. Visual comparison, if implemented

---

# Final GitHub structure

By the end, it should look approximately like:

```text
resume-screening-system/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── job_descriptions/
│
├── notebooks/
│   └── Resume_Screening_System_(1).ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── preprocessing.py
│   ├── pdf_parser.py
│   ├── skill_extraction.py
│   ├── job_parser.py
│   ├── similarity.py
│   ├── scoring.py
│   ├── ranking.py
│   ├── skill_gap.py
│   └── pipeline.py
│
├── evaluation/
│   ├── evaluate_skills.py
│   ├── evaluate_ranking.py
│   └── error_analysis.py
│
├── app/
│   └── app.py
│
├── tests/
│   ├── test_preprocessing.py
│   ├── test_skill_extraction.py
│   ├── test_similarity.py
│   ├── test_scoring.py
│   └── test_pdf_parser.py
│
├── outputs/
│   ├── figures/
│   ├── results/
│   └── screenshots/
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Important Rule for the Whole Project

The **notebook remains your experimentation space**.

Do not immediately move every line of notebook code into `src/`.

The workflow should be:

```text
Experiment in notebook
        ↓
Understand result
        ↓
Validate approach
        ↓
Decide what stays
        ↓
Refactor validated logic
        ↓
Move into src/
```

This is particularly important because your current notebook already contains experimentation with **SentenceTransformer + cosine similarity and hybrid scoring**.

We should preserve that work as evidence of experimentation rather than pretending the final approach was known from the beginning.

---

# Definition of "Done"

The project is complete when a recruiter can provide:

```text
Job Description
+
Multiple Resume PDFs
```

and receive:

```text
Candidate Ranking
        +
Overall Match
        +
Matched Skills
        +
Missing Skills
        +
Similarity
        +
Score Breakdown
        +
Ranking Explanation
```

while the GitHub repository can answer:

```text
Why was this approach chosen?
How was the data processed?
How are skills extracted?
How is similarity calculated?
How is the score calculated?
How is ranking evaluated?
Where does the system fail?
What are its limitations?
```

That is the difference between **an internship demo** and a **portfolio-quality ML project**.
