import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

DATA = Path("data/karnataka_physical_2021_2025.csv")
OUTPUT = Path("outputs/forecast_evaluation.csv")


def main():
    with DATA.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    station_col = next(
        h for h in headers if h.strip().casefold() == "station"
    )
    date_col = next(
        h for h in headers if "acquisition time" in h.casefold()
    )
    value_col = next(
        h for h in headers if "conduct" in h.casefold()
    )

    grouped = defaultdict(list)

    for row in rows:
        station = (row.get(station_col) or "").strip()
        date_text = (row.get(date_col) or "").strip()
        raw_value = (row.get(value_col) or "").strip()

        try:
            value = float(raw_value)
            date = date_text.split()[0]
            day, month, year = map(int, date.split("-"))
            date_key = (year, month, day)
        except (ValueError, TypeError):
            continue

        if station and math.isfinite(value) and value >= 0:
            grouped[station].append((date_key, value, date_text))

    results = []

    for station, observations in grouped.items():
        observations.sort(key=lambda item: item[0])

        # Evaluate only stations with enough chronological observations.
        if len(observations) < 12:
            continue

        for i in range(8, len(observations)):
            history = [item[1] for item in observations[:i]]
            actual = observations[i][1]

            # Baseline: predict the next value using the median
            # of the previous eight available observations.
            prediction = median(history[-8:])
            error = abs(actual - prediction)

            results.append({
                "station": station,
                "forecast_date": observations[i][2],
                "history_points": len(history),
                "predicted_conductivity": round(prediction, 3),
                "actual_conductivity": round(actual, 3),
                "absolute_error": round(error, 3),
            })

    OUTPUT.parent.mkdir(exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "station", "forecast_date", "history_points",
            "predicted_conductivity", "actual_conductivity",
            "absolute_error",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    if not results:
        print("No evaluation rows were produced.")
        return

    mae = sum(r["absolute_error"] for r in results) / len(results)

    print("=== AQUASENTINEL: FORECAST BASELINE EVALUATION ===")
    print("Evaluation predictions:", len(results))
    print("Stations evaluated:", len({r["station"] for r in results}))
    print("Mean absolute error:", round(mae, 3), "µS/cm")
    print("Saved:", OUTPUT)
    print("\nFirst five evaluation records:")

    for row in results[:5]:
        print(row)

    print(
        "\nThis is a median-based baseline, not a trained AI model. "
        "Predictions use earlier records only."
    )


if __name__ == "__main__":
    main()
