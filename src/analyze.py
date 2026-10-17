import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

DATA_PATH = Path("data/karnataka_physical_2021_2025.csv")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

THRESHOLD = 5000
MIN_STATION_READINGS = 8
MAD_MULTIPLIER = 3.5

STATION_COL = "Station"
DATE_COL = "Data Acquisition Time"
DISTRICT_COL = "District"


def parse_number(raw):
    """Return a finite, non-negative numeric reading, or None."""
    try:
        value = float((raw or "").strip())
        if math.isfinite(value) and value >= 0:
            return value
    except (TypeError, ValueError):
        pass
    return None


with DATA_PATH.open(encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    rows = list(reader)
    headers = reader.fieldnames or []

value_matches = [
    h for h in headers
    if "conduct" in h.casefold()
]

if len(value_matches) != 1:
    raise ValueError(
        f"Expected one conductivity column; found: {value_matches}"
    )

VALUE_COL = value_matches[0]

required = {STATION_COL, DATE_COL}
missing = required - set(headers)

if missing:
    raise ValueError(f"Missing required CSV columns: {sorted(missing)}")

if DISTRICT_COL not in headers:
    DISTRICT_COL = None

# Gather valid numeric readings by station.
station_values = defaultdict(list)
valid_count = 0
invalid_count = 0

for row in rows:
    value = parse_number(row.get(VALUE_COL))
    if value is None:
        invalid_count += 1
        continue
    valid_count += 1
    station = (row.get(STATION_COL) or "").strip()
    if station:
        station_values[station].append(value)

# Calculate station-specific robust baselines.
baselines = {}
for station, values in station_values.items():
    if len(values) < MIN_STATION_READINGS:
        continue

    center = median(values)
    mad = median([abs(value - center) for value in values])
    baselines[station] = (center, mad, len(values))

report_path = OUTPUT_DIR / "station_anomaly_review.csv"
review_count = 0
status_counts = defaultdict(int)

with report_path.open("w", encoding="utf-8", newline="") as file:
    fields = [
        "station",
        "timestamp",
        "district",
        "conductivity_us_cm",
        "station_median",
        "station_MAD",
        "robust_score",
        "dataset_extreme",
        "status",
        "review_reason",
    ]
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()

    for row in rows:
        raw = row.get(VALUE_COL)
        value = parse_number(raw)
        station = (row.get(STATION_COL) or "").strip()
        timestamp = (row.get(DATE_COL) or "").strip()
        district = (row.get(DISTRICT_COL) or "").strip() if DISTRICT_COL else ""
        reasons = []
        center = ""
        mad = ""
        score = ""
        dataset_extreme = False

        if value is None:
            status = "INVALID_OR_MISSING_READING"
            reasons.append("Reading is missing, non-numeric, negative, or non-finite.")
        else:
            if value > THRESHOLD:
                dataset_extreme = True
                reasons.append(f"Value exceeds exploratory threshold {THRESHOLD}.")

            baseline = baselines.get(station)
            if baseline is None:
                status = "INSUFFICIENT_STATION_HISTORY"
                reasons.append(
                    f"Fewer than {MIN_STATION_READINGS} valid readings for station baseline."
                )
            else:
                center, mad, count = baseline

                if mad > 0:
                    score = round(0.6745 * (value - center) / mad, 3)
                    if abs(score) > MAD_MULTIPLIER:
                        reasons.append(
                            f"Station-level robust score exceeds ±{MAD_MULTIPLIER}."
                        )
                elif value != center:
                    reasons.append(
                        "Station MAD is zero; deviation needs alternative review."
                    )

                if reasons:
                    status = "CANDIDATE_ANOMALY"
                else:
                    status = "WITHIN_BASELINE"

        if status != "WITHIN_BASELINE":
            review_count += 1

        status_counts[status] += 1

        writer.writerow({
            "station": station,
            "timestamp": timestamp,
            "district": district,
            "conductivity_us_cm": raw or "",
            "station_median": center,
            "station_MAD": mad,
            "robust_score": score,
            "dataset_extreme": dataset_extreme,
            "status": status,
            "review_reason": " ".join(reasons),
        })

summary = {
    "project": "AquaSentinel AI",
    "method": "Station-specific median absolute deviation",
    "exploratory_threshold": THRESHOLD,
    "minimum_station_readings": MIN_STATION_READINGS,
    "source_records": len(rows),
    "valid_numeric_readings": valid_count,
    "invalid_or_missing_readings": invalid_count,
    "stations_with_numeric_readings": len(station_values),
    "stations_with_baselines": len(baselines),
    "records_requiring_review": review_count,
    "status_counts": dict(status_counts),
    "report": str(report_path),
    "interpretation": (
        "Exploratory anomaly screening only; flags require verification "
        "and are not a water-safety diagnosis."
    ),
}

summary_path = OUTPUT_DIR / "analysis_summary.json"
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("=== AQUASENTINEL AI ===")
print("Method: Station-specific median absolute deviation")
print("Source records:", len(rows))
print("Valid numeric readings:", valid_count)
print("Invalid or missing readings:", invalid_count)
print("Stations with baselines:", len(baselines))
print("Records requiring review:", review_count)

for status, count in sorted(status_counts.items()):
    print(f"{status}: {count}")

print("Report:", report_path)
print("Summary:", summary_path)
print("Screening is not a water-safety diagnosis.")
