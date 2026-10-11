
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]

METRICS_FILE = ROOT / "simulation/results/vehicle_metrics.csv"
LOTS_FILE = ROOT / "shared/config/parking-lots.json"


def main():
    with open(LOTS_FILE, encoding="utf-8") as file:
        config = json.load(file)

    area_to_lot = {}

    for lot_id, lot in config["lots"].items():
        for area_id in lot["sumoParkingAreas"]:
            area_to_lot[area_id] = lot_id

    grouped = defaultdict(list)
    unknown_areas = set()

    with open(METRICS_FILE, newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            area_id = row["assigned_parking_area"]
            lot_id = area_to_lot.get(area_id)

            if lot_id is None:
                unknown_areas.add(area_id)
                continue

            grouped[lot_id].append(row)

    print("\n=== Parking Experiment Summary ===")

    for lot_id in sorted(grouped):
        vehicles = grouped[lot_id]

        successful = [
            row for row in vehicles
            if row["parking_success"].lower() == "true"
        ]

        def average_metric(rows, field):
            values = [
                float(row[field])
                for row in rows
                if row[field] not in ("", None)
            ]
            return mean(values) if values else None

        print(f"\nLot {lot_id}")
        print(f"  Vehicles: {len(vehicles)}")
        print(f"  Successfully parked: {len(successful)}")
        print(
            f"  Success rate: "
            f"{100 * len(successful) / len(vehicles):.1f}%"
        )

        for field, label in [
            ("time_to_parking", "Avg time to parking"),
            ("waiting_time", "Avg waiting time"),
            ("time_loss", "Avg time loss"),
        ]:
            value = average_metric(successful, field)
            print(
                f"  {label}: "
                f"{value:.2f}s" if value is not None
                else f"  {label}: N/A"
            )

    if unknown_areas:
        print("\nUnmapped parking areas:")
        for area_id in sorted(unknown_areas):
            print(f"  {area_id}")


if __name__ == "__main__":
    main()
