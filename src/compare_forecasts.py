import csv
import math
from collections import defaultdict
from statistics import median
from pathlib import Path

DATA = Path("data/karnataka_physical_2021_2025.csv")
OUTPUT = Path("outputs/forecast_model_comparison.csv")
OUTPUT.parent.mkdir(exist_ok=True)

with DATA.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    headers = reader.fieldnames or []
    station_col = next(h for h in headers if h.strip().casefold() == "station")
    date_col = next(h for h in headers if "acquisition time" in h.casefold())
    value_col = next(h for h in headers if "conduct" in h.casefold())
    rows = list(reader)

groups = defaultdict(list)

for row in rows:
    station = (row.get(station_col) or "").strip()
    raw_date = (row.get(date_col) or "").strip()
    raw_value = (row.get(value_col) or "").strip()

    try:
        value = float(raw_value)
        day, month, year = map(int, raw_date.split()[0].split("-"))
        date_key = (year, month, day)
    except (ValueError, TypeError, IndexError):
        continue

    if station and math.isfinite(value) and value >= 0:
        groups[station].append((date_key, value, raw_date))

results = []

for station, observations in groups.items():
    observations.sort(key=lambda item: item[0])

    for i in range(8, len(observations)):
        history = [item[1] for item in observations[i - 8:i]]
        actual = observations[i][1]

        last_prediction = history[-1]
        median_prediction = median(history)

        results.append({
            "station": station,
            "forecast_date": observations[i][2],
            "history_points": len(history),
            "actual_conductivity": actual,
            "last_reading_prediction": last_prediction,
            "median_8_prediction": median_prediction,
            "last_reading_absolute_error": abs(actual - last_prediction),
            "median_8_absolute_error": abs(actual - median_prediction),
        })

if not results:
    raise SystemExit("No forecast records were generated.")

with OUTPUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

def report(label, error_key, subset):
    errors = [r[error_key] for r in subset]
    print(f"\n{label}")
    print("Evaluations:", len(errors))
    print("MAE:", round(sum(errors) / len(errors), 2))
    print("Median absolute error:", round(median(errors), 2))

print("=== AQUASENTINEL: FAIR FORECAST COMPARISON ===")
print("Same historical forecast dates for both methods.")

report("Last-reading baseline", "last_reading_absolute_error", results)
report("Eight-reading median baseline", "median_8_absolute_error", results)

normal = [r for r in results if r["actual_conductivity"] <= 5000]
report("Last-reading baseline (actual <= 5000)", "last_reading_absolute_error", normal)
report("Eight-reading median (actual <= 5000)", "median_8_absolute_error", normal)

print("\nSaved:", OUTPUT)
print("Historical baseline comparison only; neither method is a trained AI model.")
