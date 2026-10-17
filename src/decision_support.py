import csv
from pathlib import Path

INPUT = Path("outputs/station_anomaly_review.csv")
OUTPUT = Path("outputs/decision_support_queue.csv")


def classify(row):
    status = row.get("status", "")
    reason = row.get("review_reason", "")
    score_text = row.get("robust_score", "").strip()

    if status == "INVALID_OR_MISSING_READING":
        return (
            "DATA_QUALITY",
            "Check the original record and arrange a repeat measurement if needed."
        )

    if status == "INSUFFICIENT_STATION_HISTORY":
        return (
            "INSUFFICIENT_EVIDENCE",
            "Collect more readings before establishing a reliable station baseline."
        )

    try:
        score = abs(float(score_text)) if score_text else 0.0
    except ValueError:
        score = 0.0

    if score >= 10:
        priority = "HIGH_REVIEW"
        action = (
            "Verify the measurement, units and source record; "
            "review nearby readings and consider confirmatory sampling."
        )
    elif score >= 5:
        priority = "MEDIUM_REVIEW"
        action = (
            "Compare with recent station history and check for "
            "a repeatable deviation."
        )
    else:
        priority = "ROUTINE_REVIEW"
        action = "Review the reading and station baseline."

    if "exploratory threshold" in reason.lower():
        action += " Check whether the high conductivity value is valid."

    return priority, action


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Analysis report not found: {INPUT}. Run src/analyze.py first."
        )

    with INPUT.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("Analysis report contains no records.")

    fields = list(rows[0].keys()) + [
        "review_priority",
        "recommended_action",
        "decision_support_note",
    ]

    for row in rows:
        priority, action = classify(row)
        row["review_priority"] = priority
        row["recommended_action"] = action
        row["decision_support_note"] = (
            "Screening result only; not a water-safety diagnosis."
        )

    priority_order = {
        "HIGH_REVIEW": 0,
        "MEDIUM_REVIEW": 1,
        "ROUTINE_REVIEW": 2,
        "DATA_QUALITY": 3,
        "INSUFFICIENT_EVIDENCE": 4,
    }

    rows.sort(
        key=lambda r: (
            priority_order.get(r["review_priority"], 5),
            -abs(float(r["robust_score"]))
            if r.get("robust_score", "").strip()
            else 0,
        )
    )

    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print("=== AQUASENTINEL AI: DECISION SUPPORT ===")
    print(f"Records processed: {len(rows)}")
    print(f"Output: {OUTPUT}")
    print("\nPriority counts:")

    for priority in priority_order:
        count = sum(r["review_priority"] == priority for r in rows)
        print(f"{priority}: {count}")

    print("\nTop 5 records for review:")
    for row in rows[:5]:
        print(
            f"- {row.get('station', 'Unknown')} | "
            f"{row.get('district', 'Unknown')} | "
            f"Value: {row.get('conductivity_us_cm', '')} | "
            f"Priority: {row['review_priority']}"
        )


if __name__ == "__main__":
    main()
