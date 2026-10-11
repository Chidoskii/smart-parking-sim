
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPLICIT_FILE = ROOT / "shared/geojson/parking-spaces.geojson"
PREVIEW_FILE = ROOT / "shared/geojson/parking-spaces-preview.geojson"
MIXED_FILE = ROOT / "shared/geojson/parking-spaces-mixed.geojson"
OUTPUT_FILE = ROOT / "shared/geojson/parking-spaces-combined.geojson"

CAPACITY_FILE = ROOT / "shared/config/parking-capacity.json"
LOTS_FILE = ROOT / "shared/config/parking-lots.json"
PARKING_XML = ROOT / "simulation/sumo/additionals/parking.add.xml"

# Keep explicit spaces and generated preview spaces intact.
# The 40 mixed-area roadside spaces will be added by a
# separate geometry-generation pass, not copied or invented here.


def load_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def main():
    explicit_data = load_json(EXPLICIT_FILE)
    preview_data = load_json(PREVIEW_FILE)
    mixed_data = load_json(MIXED_FILE)
    capacity_data = load_json(CAPACITY_FILE)
    lots_data = load_json(LOTS_FILE)["lots"]

    area_to_lot = {}

    for lot_id, lot in lots_data.items():
        for area_id in lot["sumoParkingAreas"]:
            if area_id in area_to_lot:
                raise ValueError(
                    f"Duplicate area assignment: {area_id}"
                )
            area_to_lot[area_id] = lot_id

    combined = []
    seen_ids = set()

    for source_name, data in [
        ("explicit", explicit_data),
        ("provisional", preview_data),
        ("provisional", mixed_data),
    ]:
        for feature in data["features"]:
            properties = feature["properties"].copy()
            space_id = properties["id"]
            area_id = properties["parkingAreaId"]

            if space_id in seen_ids:
                raise ValueError(
                    f"Duplicate space ID: {space_id}"
                )

            if area_id not in area_to_lot:
                raise ValueError(
                    f"Unknown parking area: {area_id}"
                )

            seen_ids.add(space_id)

            properties["campusLot"] = area_to_lot[area_id]
            properties["status"] = "available"

            if source_name == "explicit":
                properties["geometryType"] = "explicit"

            combined.append({
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": properties,
            })

    counts = Counter(
        feature["properties"]["parkingAreaId"]
        for feature in combined
    )

    expected_areas = capacity_data["areas"]

    print("\nParking-area capacity validation")
    print("-" * 65)

    missing_total = 0
    unexpected_total = 0

    for area_id, config in sorted(expected_areas.items()):
        expected = config["capacity"]
        actual = counts[area_id]

        difference = expected - actual

        if difference != 0:
            print(
                f"{area_id:<22} "
                f"expected={expected:<5} "
                f"actual={actual:<5} "
                f"missing={difference}"
            )

        if difference > 0:
            missing_total += difference
        elif difference < 0:
            unexpected_total += -difference

    unknown_areas = set(counts) - set(expected_areas)

    if unknown_areas:
        raise ValueError(
            f"Areas missing from capacity config: {unknown_areas}"
        )

    lot_counts = Counter(
        feature["properties"]["campusLot"]
        for feature in combined
    )

    if missing_total != 0 or unexpected_total != 0:
        raise ValueError(
            f"Capacity validation failed: "
            f"{missing_total} missing, "
            f"{unexpected_total} excess"
        )

    if len(combined) != capacity_data["totalCapacity"]:
        raise ValueError(
            f"Expected {capacity_data['totalCapacity']} spaces, "
            f"found {len(combined)}"
        )

    print("\nCurrent combined geometry")
    for lot in ["J", "M", "PS1", "F2"]:
        print(f"  {lot}: {lot_counts[lot]:,}")

    print(f"\nTotal features: {len(combined):,}")
    print(f"Unique IDs: {len(seen_ids):,}")
    print(f"Missing capacity: {missing_total:,}")
    print(f"Excess geometry: {unexpected_total:,}")

    # This intermediate output is intentional.
    # Do not replace the active parking-spaces.geojson yet.
    output = {
        "type": "FeatureCollection",
        "features": combined,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2)

    print(f"\nIntermediate file saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
