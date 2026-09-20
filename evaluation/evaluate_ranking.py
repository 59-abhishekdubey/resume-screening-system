import csv
import os
from collections import defaultdict


def evaluate_ranking(
    labeled_path: str = "outputs/results/labeling_template.csv",
    output_path: str = "outputs/results/ranking_eval.csv",
) -> None:
    # Read labeled pairs
    labeled_pairs = []
    with open(labeled_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            labeled_pairs.append(
                {
                    "pair_id": row["pair_id"],
                    "resume_id": row["resume_id"],
                    "job_role": row["job_role"],
                    "relevant": int(row["relevant"]),
                    "notes": row.get("notes", ""),
                }
            )

    # Build per-resume: job_role -> tfidf score from similarity_experiment.csv
    resume_scores = defaultdict(dict)  # resume_id -> {job_role: score}
    sim_path = "outputs/results/similarity_experiment.csv"
    if os.path.exists(sim_path):
        with open(sim_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rid = row["resume_id"]
                role = row["job_role"]
                score = float(row["tfidf_score"])
                resume_scores[rid][role] = score

    # For each resume, rank job roles by score and compute P@K / R@K
    results = []
    for pair in labeled_pairs:
        pid = pair["pair_id"]
        rid = pair["resume_id"]
        role = pair["job_role"]
        relevant = pair["relevant"]

        scores = resume_scores.get(rid, {})
        all_roles = sorted(scores.keys(), key=lambda r: scores[r], reverse=True)

        # Find which roles are relevant for this resume
        relevant_roles = set()
        for p in labeled_pairs:
            if p["resume_id"] == rid:
                relevant_roles.add(p["job_role"])

        n_relevant = len(relevant_roles) if relevant_roles else 1  # avoid div0
        pair_results = {"pair_id": pid, "resume_id": rid, "job_role": role}

        # Compute P@K and R@K for K = 1, 3, 5, 10
        for k in [1, 3, 5, 10]:
            if k > len(all_roles):
                # Can't retrieve more than available roles
                pair_results[f"precision@{k}"] = 0.0
                pair_results[f"recall@{k}"] = 0.0
            else:
                k_val = k
                top_k = set(all_roles[:k_val])
                retrieved_relevant = len(top_k & relevant_roles)

                precision_k = retrieved_relevant / k_val if k_val > 0 else 0.0
                recall_k = retrieved_relevant / n_relevant if n_relevant > 0 else 0.0

                pair_results[f"precision@{k}"] = precision_k
                pair_results[f"recall@{k}"] = recall_k

        results.append(pair_results)

    # Write output CSV
    fieldnames = [
        "pair_id", "resume_id", "job_role",
        "precision@1", "recall@1",
        "precision@3", "recall@3",
        "precision@5", "recall@5",
        "precision@10", "recall@10",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"Wrote ranking evaluation to {output_path}")
    # Print summary
    for k in [1, 3, 5]:
        prec_vals = [r[f"precision@{k}"] for r in results]
        rec_vals = [r[f"recall@{k}"] for r in results]
        print(f"P@{k}: {sum(prec_vals)/len(prec_vals):.4f} (mean), R@{k}: {sum(rec_vals)/len(rec_vals):.4f} (mean)")


if __name__ == "__main__":
    evaluate_ranking()