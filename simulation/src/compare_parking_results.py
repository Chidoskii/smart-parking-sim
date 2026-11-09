
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "simulation" / "results"

SCENARIOS = ("baseline", "availability", "smart")

METRICS = [
    "time_to_parking",
    "parking_search_time",
    "waiting_time",
    "time_loss",
    "distance_m",
    "co2_g",
    "fuel_g",
    "walking_distance_m",
    "walking_time_s",
    "destination_displacement_m",
    "estimated_walking_time_s",
    "actual_parking_duration_s",
    "return_travel_time_s",
    "return_distance_m",
]


def latest_results(scenario):
    files = list(
        (RESULTS_DIR / scenario).glob(
            "run_*/vehicle_metrics.csv"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No results found for {scenario}"
        )

    return max(
        files,
        key=lambda path: int(
            path.parent.name.split("_")[-1]
        ),
    )


def load_results(path):
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def average(rows, metric):
    values = [
        float(row[metric])
        for row in rows
        if row.get("parking_success", "").lower() == "true"
        and row.get(metric) not in ("", None)
    ]

    return sum(values) / len(values) if values else None


def count_true(rows, field):
    return sum(
        row.get(field, "").lower() == "true"
        for row in rows
    )


def total_reassignments(rows):
    return sum(
        int(row.get("parking_reassignments") or 0)
        for row in rows
    )


def format_value(value):
    return f"{value:.2f}" if value is not None else "N/A"


def percent_change(value, baseline):
    if value is None or baseline is None or baseline == 0:
        return "N/A"

    return f"{(value - baseline) / baseline * 100:+.2f}%"


def main():
    results = {}

    print("\nSELECTED SIMULATION RUNS")
    print("=" * 75)

    for scenario in SCENARIOS:
        path = latest_results(scenario)
        rows = load_results(path)

        results[scenario] = rows

        print(f"{scenario.capitalize():14} {path}")

    print("\nPERFORMANCE COMPARISON")
    print("=" * 105)

    print(
        f"{'Metric':32}"
        f"{'Baseline':>12}"
        f"{'Availability':>15}"
        f"{'Smart':>12}"
        f"{'Avail %':>15}"
        f"{'Smart %':>15}"
    )

    print("-" * 105)

    for metric in METRICS:
        b = average(results["baseline"], metric)
        a = average(results["availability"], metric)
        s = average(results["smart"], metric)

        print(
            f"{metric:32}"
            f"{format_value(b):>12}"
            f"{format_value(a):>15}"
            f"{format_value(s):>12}"
            f"{percent_change(a, b):>15}"
            f"{percent_change(s, b):>15}"
        )

    print("\nVEHICLE LIFECYCLE SUMMARY")
    print("=" * 75)

    print(
        f"{'Metric':32}"
        f"{'Baseline':>12}"
        f"{'Availability':>15}"
        f"{'Smart':>12}"
    )

    print("-" * 75)

    summary = {
        "Vehicles": lambda r: len(r),
        "Parking successes": lambda r: count_true(
            r, "parking_success"
        ),
        "Completed return trips": lambda r: count_true(
            r, "completed_return_trip"
        ),
        "Parking reassignments": total_reassignments,
        "Teleported vehicles": lambda r: count_true(
            r, "teleported"
        ),
    }

    for label, calculate in summary.items():
        values = [
            calculate(results[scenario])
            for scenario in SCENARIOS
        ]

        print(
            f"{label:32}"
            f"{values[0]:>12}"
            f"{values[1]:>15}"
            f"{values[2]:>12}"
        )


if __name__ == "__main__":
    main()
