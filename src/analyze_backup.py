import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

SOURCE = Path("data/karnataka_physical_2021_2025.csv")
REPORT = Path("outputs/station_anomaly_review.csv")
SUMMARY = Path("outputs/analysis_summary.json")
THRESHOLD = 3.5
MIN_STATION_READINGS = 8


def find_column(headers, predicate, description):
    for header in headers:
        if predicate(header.lower()):
            return header
    raise ValueError(f"Could not find column: {description}")


def main():
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []

    station_col = find_column(
        headers, lambda h: h == "station", "station"
    )
    value_col = find_column(
        headers, lambda h: "conduct" in h, "conductivity"
    )
    date_col = find_column(
        headers, lambda h: "acquisition time" in h, "timestamp"
    )

    records = []
    station_groups = defaultdict(list)
    invalid_count = 0

    for row in rows:
        raw = (row.get(value_col) or "").strip()

        try:
            value = float(raw)
        except ValueError:
            invalid_count += 1
            continue

        if not value >= 0 or value == float("inf"):
            invalid_count += 1
            continue

        station = (row.get(station_col) or "").strip()
        record = {
            "station": station,
            "timestamp": (row.get(date_col) or "").strip(),
            "conductivity_uS_cm": value,
            "station_readings": "",
            "station_median": "",
            "station_MAD": "",
            "robust_score": "",
            "status": "",
        }
        records.append(record)
        station_groups[station].append(record)

    counts = defaultdict(int)

    for station, group in station_groups.items():
        values = [r["conductivity_uS_cm"] for r in group]
        center = median(values)
        mad = median([abs(v - center) for v in values])

        for record in group:
            record["station_readings"] = len(group)
            record["station_median"] = round(center, 3)
            record["station_MAD"] = round(mad, 3)

            if len(group) < MIN_STATION_READINGS:
                status = "INSUFFICIENT_STATION_HISTORY"
            elif mad == 0:
                status = "REVIEW_BASELINE_MAD_ZERO"
            else:
                score = 0.6745 * (
                    record["conductivity_uS_cm"] - center
                ) / mad
                record["robust_score"] = round(score, 3)
                status = (
                    "CANDIDATE_ANOMALY"
                    if abs(score) > THRESHOLD
                    else "WITHIN_BASELINE"
                )

            record["status"] = status
            counts[status] += 1

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    fields = list(records[0].keys()) if records else []

    with REPORT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    summary = {
        "project": "AquaSentinel AI",
        "method": "Station-specific median absolute deviation",
        "threshold": THRESHOLD,
        "minimum_station_readings": MIN_STATION_READINGS,
        "source_records": len(rows),
        "numeric_readings": len(records),
        "invalid_or_missing_readings": invalid_count,
        "stations_with_numeric_readings": len(station_groups),
        "status_counts": dict(counts),
        "report": str(REPORT),
        "interpretation": (
            "Exploratory anomaly screening; not a water-safety diagnosis."
        ),
    }

    SUMMARY.write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print("=== AQUASENTINEL AI ===")
    print("Method:", summary["method"])
    print("Threshold:", THRESHOLD)
    print("Source records:", len(rows))
    print("Numeric readings:", len(records))
    print("Stations:", len(station_groups))
    for status, count in sorted(counts.items()):
        print(f"{status}: {count}")
    print("Report:", REPORT)
    print("Summary:", SUMMARY)
    print("Screening is not a water-safety diagnosis.")


if __name__ == "__main__":
    main()
