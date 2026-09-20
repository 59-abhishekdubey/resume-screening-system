import csv
import os
from collections import defaultdict


def load_csv(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def error_analysis(
    skill_eval_path: str = "outputs/results/skill_eval.csv",
    ranking_eval_path: str = "outputs/results/ranking_eval.csv",
    labeling_path: str = "outputs/results/labeling_template.csv",
    output_path: str = "outputs/results/error_cases.csv",
) -> None:
    skill_rows = load_csv(skill_eval_path)
    ranking_rows = load_csv(ranking_eval_path)
    labeled_pairs = load_csv(labeling_path)

    case_rows = []

    # Index skill rows by skill name
    skill_by_name = defaultdict(list)
    for row in skill_rows:
        skill_name = row["skill"]
        if skill_name in ("MICRO", "MACRO"):
            continue
        skill_by_name[skill_name].append(row)

    # Index ranking rows by pair_id
    ranking_by_pair = defaultdict(list)
    for row in ranking_rows:
        pairing_id = row.get("pair_id", "")
        ranking_by_pair[pairing_id].append(row)

    # Index labeled pairs by pair_id
    labeled_by_id = {}
    for row in labeled_pairs:
        labeled_by_id[row["pair_id"]] = row

    # ---- Missed skills ----
    for skill_name, skill_rows_list in skill_by_name.items():
        for srow in skill_rows_list:
            # Get the pair_id somehow - we need to trace back
            # skill_eval.csv doesn't have pair_id directly; use ranking_eval to map
            pass

    # Instead, let's analyze per labeled pair
    for lp in labeled_pairs:
        pair_id = lp["pair_id"]
        rid = lp["resume_id"]
        role = lp["job_role"]
        relevant = lp["relevant"]

        # Find ranking results for this pair
        ranking_rows_for_pair = ranking_by_pair.get(pair_id, [])

        # Find skill eval info for this resume
        # skill_eval skills are global; we need to map resume_id to skill performance
        # For now, check if any skill has low F1 for this resume's expected skills
        for srow in skill_rows:
            if srow["skill"] in ("MICRO", "MACRO"):
                continue
            # If skill has low precision/recall, it's a missed/false skill case
            prec = float(srow.get("precision", 0))
            rec = float(srow.get("recall", 0))
            f1 = float(srow.get("f1", 0))

            if f1 < 0.3:
                # Determine case type
                if rec < prec:
                    case_type = "false_skill"
                else:
                    case_type = "missed_skill"

                case_rows.append(
                    {
                        "case_type": case_type,
                        "description": f"Skill '{srow['skill']}' for pair {pair_id} (resume {rid}, {role}) has low F1={f1:.2f}",
                        "root_cause_guess": "Skill extraction regex/alias mismatch or JD terminology differs from resume language",
                    }
                )

    # ---- Wrong rank cases ----
    for row in ranking_rows:
        pair_id = row.get("pair_id", "")
        prec1 = float(row.get("precision@1", 0))
        if prec1 < 0.2 and pair_id in labeled_by_id:
            lp = labeled_by_id[pair_id]
            if lp["relevant"] == 1:
                case_rows.append(
                    {
                        "case_type": "wrong_rank",
                        "description": f"Pair {pair_id} is relevant but Rank@1 precision low ({prec1:.2f})",
                        "root_cause_guess": "Scoring formula (ESW) or similarity weight miscalibrated for this resume-JD pair",
                    }
                )

    # ---- Low similarity high relevance cases ----
    for row in ranking_rows:
        pair_id = row.get("pair_id", "")
        sim_score = float(row.get("similarity_score", 0)) if "similarity_score" in row else None
        rel = row.get("relevant", 0)
        if sim_score is not None and sim_score < 0.2 and rel == 1 and pair_id in labeled_by_id:
            lp = labeled_by_id[pair_id]
            case_rows.append(
                {
                    "case_type": "low_similarity_high_relevance",
                    "description": f"Pair {pair_id} is relevant (relevant={lp['relevant']}) but similarity low ({sim_score:.2f})",
                    "root_cause_guess": "TF-IDF and semantic scores disagree; resume uses different phrasing than JD keywords",
                }
            )

    # Group by case_type and count
    grouped = defaultdict(list)
    for row in case_rows:
        grouped[row["case_type"]].append(row)

    # Write output
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["case_type", "description", "root_cause_guess"]
        )
        writer.writeheader()
        for case_type in sorted(grouped.keys()):
            for row in grouped[case_type]:
                writer.writerow(row)

    print(f"Wrote error cases to {output_path}")
    for case_type in sorted(grouped.keys()):
        print(f"  {case_type}: {len(grouped[case_type])} cases")

    # Print top 10 cases grouped by type
    printed = 0
    for case_type in sorted(grouped.keys()):
        for row in grouped[case_type]:
            if printed < 10:
                print(f"[{case_type}] {row['description']}")
                printed += 1


if __name__ == "__main__":
    error_analysis()