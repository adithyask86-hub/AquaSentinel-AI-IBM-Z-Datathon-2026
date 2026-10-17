import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
import numpy as np

DATA = Path("data/karnataka_physical_2021_2025.csv")
OUTPUT = Path("outputs/linear_forecast_evaluation.csv")
WINDOW = 8

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
    try:
        value = float((row.get(value_col) or "").strip())
        day, month, year = map(int, raw_date.split()[0].split("-"))
        date_key = (year, month, day)
    except (ValueError, TypeError, IndexError):
        continue
    if station and math.isfinite(value) and value >= 0:
        groups[station].append((date_key, value, raw_date))

# Build chronological training and testing examples.
examples = []
for station, obs in groups.items():
    obs.sort(key=lambda x: x[0])
    values = [x[1] for x in obs]
    for i in range(WINDOW, len(values)):
        examples.append({
            "station": station,
            "date": obs[i][2],
            "history": values[i-WINDOW:i],
            "actual": values[i],
        })

# Split by each station's timeline: earlier observations train,
# later observations test. Fit on training data only.
train_x, train_y, test = [], [], []
by_station = defaultdict(list)
for ex in examples:
    by_station[ex["station"]].append(ex)

for station_examples in by_station.values():
    cut = max(1, int(len(station_examples) * 0.7))
    for ex in station_examples[:cut]:
        train_x.append(ex["history"])
        train_y.append(ex["actual"])
    test.extend(station_examples[cut:])

if len(train_x) < 10 or len(test) < 1:
    raise SystemExit("Not enough training/testing examples.")

# Standardize using training data only, and fit linear regression
# with a small ridge term for numerical stability.
X = np.asarray(train_x, dtype=float)
y = np.asarray(train_y, dtype=float)
mu = X.mean(axis=0)
sigma = X.std(axis=0)
sigma[sigma == 0] = 1.0
Xs = (X - mu) / sigma
design = np.column_stack([np.ones(len(Xs)), Xs])
penalty = np.eye(design.shape[1]) * 1e-6
penalty[0, 0] = 0
weights = np.linalg.solve(design.T @ design + penalty, design.T @ y)

results = []
for ex in test:
    x = (np.asarray(ex["history"], dtype=float) - mu) / sigma
    prediction = float(np.r_[1.0, x] @ weights)
    prediction = max(0.0, prediction)
    actual = ex["actual"]
    results.append({
        "station": ex["station"],
        "forecast_date": ex["date"],
        "actual_conductivity": actual,
        "linear_prediction": round(prediction, 3),
        "median_8_prediction": round(median(ex["history"]), 3),
        "linear_absolute_error": abs(actual - prediction),
        "median_8_absolute_error": abs(actual - median(ex["history"])),
    })

with OUTPUT.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

def report(label, key, subset):
    errors = [r[key] for r in subset]
    print(f"\n{label}")
    print("Test records:", len(errors))
    print("MAE:", round(sum(errors) / len(errors), 2))
    print("Median absolute error:", round(median(errors), 2))

print("=== AQUASENTINEL: LINEAR FORECAST MODEL ===")
print("Training examples:", len(train_x))
print("Held-out test examples:", len(test))
report("Fitted linear regression", "linear_absolute_error", results)
report("Median baseline on same test records", "median_8_absolute_error", results)

normal = [r for r in results if r["actual_conductivity"] <= 5000]
if normal:
    report("Linear regression (actual <= 5000)", "linear_absolute_error", normal)
    report("Median baseline (actual <= 5000)", "median_8_absolute_error", normal)

print("\nSaved:", OUTPUT)
print("Historical test only; not validated on live sensor data.")
