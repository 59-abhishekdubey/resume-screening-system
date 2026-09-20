import csv
from collections import Counter
from typing import Set, Dict, List


def compute_precision_recall_f1(
    expected: Set[str], predicted: Set[str]
) -> Dict[str, float]:
    true_positives = len(expected & predicted)
    false_positives = len(predicted - expected)
    false_negatives = len(expected - predicted)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1, "tp": true_positives, "fp": false_positives, "fn": false_negatives}


def evaluate_skills(
    labels_path: str = "outputs/results/skill_eval_labels.csv",
    output_path: str = "outputs/results/skill_eval.csv",
) -> None:
    skill_metrics: Dict[str, Dict[str, float]] = {}
    all_skills = set()

    total_tp = 0.0
    total_fp = 0.0
    total_fn = 0.0

    with open(labels_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            expected_str = row.get("expected_skills", "") or ""
            predicted_str = row.get("predicted_skills", "") or ""

            expected_skills = {
                s.strip() for s in expected_str.split(",") if s.strip()
            }
            predicted_skills = {
                s.strip() for s in predicted_str.split(",") if s.strip()
            }

            all_skills.update(expected_skills)
            all_skills.update(predicted_skills)

            metrics = compute_precision_recall_f1(expected_skills, predicted_skills)
            for skill in all_skills:
                if skill not in skill_metrics:
                    skill_metrics[skill] = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "evaluations": 0, "tp": 0.0, "fp": 0.0, "fn": 0.0}
                skill_metrics[skill]["evaluations"] = skill_metrics[skill].get("evaluations", 0) + 1
                skill_metrics[skill]["precision"] = skill_metrics[skill].get("precision", 0.0) + metrics["precision"]
                skill_metrics[skill]["recall"] = skill_metrics[skill].get("recall", 0.0) + metrics["recall"]
                skill_metrics[skill]["f1"] = skill_metrics[skill].get("f1", 0.0) + metrics["f1"]
                skill_metrics[skill]["tp"] = skill_metrics[skill].get("tp", 0.0) + metrics["tp"]
                skill_metrics[skill]["fp"] = skill_metrics[skill].get("fp", 0.0) + metrics["fp"]
                skill_metrics[skill]["fn"] = skill_metrics[skill].get("fn", 0.0) + metrics["fn"]

            total_tp += metrics["tp"]
            total_fp += metrics["fp"]
            total_fn += metrics["fn"]

    # Compute per-skill average metrics
    rows = []
    for skill in sorted(skill_metrics.keys()):
        m = skill_metrics[skill]
        avg_precision = m["precision"] / m["evaluations"] if m["evaluations"] > 0 else 0.0
        avg_recall = m["recall"] / m["evaluations"] if m["evaluations"] > 0 else 0.0
        avg_f1 = m["f1"] / m["evaluations"] if m["evaluations"] > 0 else 0.0
        rows.append(
            {
                "skill": skill,
                "evaluations": m["evaluations"],
                "precision": round(avg_precision, 4),
                "recall": round(avg_recall, 4),
                "f1": round(avg_f1, 4),
            }
        )

    # Compute micro-averaged metrics
    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (2 * micro_precision * micro_recall / (micro_precision + micro_recall)) if (micro_precision + micro_recall) > 0 else 0.0

    # Compute macro-averaged metrics (mean of per-skill averages)
    precisions = []
    recalls = []
    f1s = []
    for m in skill_metrics.values():
        if m["evaluations"] > 0:
            precisions.append(m["precision"] / m["evaluations"])
            recalls.append(m["recall"] / m["evaluations"])
            f1s.append(m["f1"] / m["evaluations"])
        else:
            precisions.append(0.0)
            recalls.append(0.0)
            f1s.append(0.0)
    macro_precision = sum(precisions) / len(precisions) if precisions else 0.0
    macro_recall = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0

    rows.append(
        {
            "skill": "MICRO",
            "evaluations": "",
            "precision": round(micro_precision, 4),
            "recall": round(micro_recall, 4),
            "f1": round(micro_f1, 4),
        }
    )
    rows.append(
        {
            "skill": "MACRO",
            "evaluations": "",
            "precision": round(macro_precision, 4),
            "recall": round(macro_recall, 4),
            "f1": round(macro_f1, 4),
        }
    )

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["skill", "evaluations", "precision", "recall", "f1"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote skill evaluation to {output_path}")
    print(f"Skills evaluated: {len(skill_metrics)}")
    print(f"Micro Precision: {micro_precision:.4f}, Micro Recall: {micro_recall:.4f}, Micro F1: {micro_f1:.4f}")
    print(f"Macro Precision: {macro_precision:.4f}, Macro Recall: {macro_recall:.4f}, Macro F1: {macro_f1:.4f}")


if __name__ == "__main__":
    evaluate_skills()