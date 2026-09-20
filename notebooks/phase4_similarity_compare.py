# Notebook: phase4_similarity_compare.py
# Comparison script for TF-IDF vs semantic similarity.
# Usage: python notebooks/phase4_similarity_compare.py
#
# Loads sample_jobs.json + N resumes from Resume.csv,
# runs both methods for each (resume, JD) pair,
# outputs similarity_experiment.csv and similarity_distribution.png.

import json
import csv
import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # project root

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.similarity import tfidf_similarity, semantic_similarity, batch_similarity

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
N = 50  # number of resumes to sample; adjust if >2 GB RAM for 200 pairs
JD_SOURCE = "data/raw/sample_jobs.json"
RESUME_SOURCE = "data/raw/Resume.csv"
OUTPUT_CSV = "outputs/results/similarity_experiment.csv"
OUTPUT_FIG = "outputs/figures/similarity_distribution.png"

# ---------------------------------------------------------------------------
# Load job descriptions
# ---------------------------------------------------------------------------
with open(JD_SOURCE, "r", encoding="utf-8") as f:
    jobs = json.load(f)

# Filter to only jobs with non-empty descriptions
valid_jobs = []
for j in jobs:
    if j.get("description", "").strip():
        valid_jobs.append(j)

print(f"Loaded {len(valid_jobs)} job descriptions with content out of {len(jobs)} total")

# ---------------------------------------------------------------------------
# Load resumes from CSV
# ---------------------------------------------------------------------------
resumes = []
with open(RESUME_SOURCE, "r", encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= N:
            break
        resumes.append(row)

print(f"Loaded {len(resumes)} resumes (limit N={N})")

# If not enough resumes, adjust
if len(resumes) < 10:
    print("WARNING: Not enough resumes for ≥50 rows. Increase N.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Run similarity computations
# ---------------------------------------------------------------------------
rows = []

for resume in resumes:
    rid = resume["ID"]
    rtext = resume["Resume_str"]

    for job in valid_jobs:
        jid = job.get("role", "Unknown")
        jtext = job.get("description", "").strip()

        # Both short-circuit to 0.0 if either text is empty
        tfidf_score = tfidf_similarity(rtext, jtext)
        sem_score = semantic_similarity(rtext, jtext)

        rows.append({
            "resume_id": rid,
            "job_role": jid,
            "tfidf_score": tfidf_score,
            "semantic_score": sem_score,
            "abs_diff": abs(tfidf_score - sem_score),
        })

print(f"Computed {len(rows)} similarity pairs")

# ---------------------------------------------------------------------------
# Write CSV
# ---------------------------------------------------------------------------
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["resume_id", "job_role", "tfidf_score", "semantic_score", "abs_diff"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {OUTPUT_CSV} with {len(rows)} rows")

# ---------------------------------------------------------------------------
# Plot distribution histogram
# ---------------------------------------------------------------------------
tfidf_scores = [r["tfidf_score"] for r in rows]
sem_scores = [r["semantic_score"] for r in rows]

plt.figure(figsize=(10, 6))
plt.hist(tfidf_scores, bins=30, alpha=0.5, label="TF-IDF", color="steelblue")
plt.hist(sem_scores, bins=30, alpha=0.5, label="Semantic", color="darkorange")
plt.xlabel("Similarity score")
plt.ylabel("Frequency")
plt.title("TF-IDF vs Semantic Similarity Distribution")
plt.legend()
plt.grid(alpha=0.3)
os.makedirs(os.path.dirname(OUTPUT_FIG), exist_ok=True)
plt.savefig(OUTPUT_FIG, dpi=150, bbox_inches="tight")
plt.close()
print(f"Wrote {OUTPUT_FIG}")

# ---------------------------------------------------------------------------
# Top 5 pairs with largest |tfidf − semantic|
# ---------------------------------------------------------------------------
top_pairs = sorted(rows, key=lambda r: r["abs_diff"], reverse=True)[:5]
print("\nTop 5 pairs where |TF-IDF - Semantic| is largest:")
for p in top_pairs:
    print(f"  resume_id={p['resume_id']}, job_role={p['job_role']}")
    print(f"    TF-IDF: {p['tfidf_score']:.4f}, Semantic: {p['semantic_score']:.4f}, |diff|: {p['abs_diff']:.4f}")

print("\nDone.")