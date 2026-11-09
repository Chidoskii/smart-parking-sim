import argparse
import json
import random
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCE_FILE = (
    ROOT / "simulation/sumo/additionals/parking.add.xml"
)

OUTPUT_DIR = (
    ROOT / "simulation/sumo/scenarios/high_occupancy"
)


def generate_occupancy(target=0.90, seed=42):
    rng = random.Random(seed)

    tree = ET.parse(SOURCE_FILE)
    root = tree.getroot()

    areas = root.findall("parkingArea")

    physical_capacity = {
        area.get("id"): int(area.get("roadsideCapacity"))
        for area in areas
    }

    total_capacity = sum(physical_capacity.values())
    target_occupied = round(total_capacity * target)

    # Distribute occupied spaces with randomized area-level variation.
    # Each area receives an initial occupancy target near the
    # campus-wide target, bounded by its physical capacity.
    occupied = {}

    for area_id, capacity in physical_capacity.items():
        rate = min(1.0, max(0.0, rng.gauss(target, 0.12)))
        occupied[area_id] = round(capacity * rate)

    # Correct the distribution to match the campus-wide target.
    difference = target_occupied - sum(occupied.values())

    while difference != 0:
        if difference > 0:
            eligible = [
                area_id for area_id, capacity in physical_capacity.items()
                if occupied[area_id] < capacity
            ]
            if not eligible:
                raise RuntimeError("Cannot increase occupancy further.")

            area_id = rng.choice(eligible)
            occupied[area_id] += 1
            difference -= 1
        else:
            eligible = [
                area_id for area_id in occupied
                if occupied[area_id] > 0
            ]
            if not eligible:
                raise RuntimeError("Cannot decrease occupancy further.")

            area_id = rng.choice(eligible)
            occupied[area_id] -= 1
            difference += 1

    metadata = {
        "scenario": "high_occupancy",
        "seed": seed,
        "target_occupancy_rate": target,
        "physical_capacity": total_capacity,
        "modeled_initial_occupied": sum(occupied.values()),
        "effective_capacity": total_capacity - sum(occupied.values()),
        "areas": {},
    }

    for area in areas:
        area_id = area.get("id")
        capacity = physical_capacity[area_id]
        initial_occupied = occupied[area_id]
        available = capacity - initial_occupied

        # SUMO will use the reduced capacity.
        area.set("roadsideCapacity", str(available))

        metadata["areas"][area_id] = {
            "physical_capacity": capacity,
            "modeled_initial_occupied": initial_occupied,
            "effective_capacity": available,
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parking_output = OUTPUT_DIR / f"parking_seed_{seed}.add.xml"
    metadata_output = OUTPUT_DIR / f"occupancy_seed_{seed}.json"

    ET.indent(tree, space="    ")
    tree.write(
        parking_output,
        encoding="utf-8",
        xml_declaration=True,
    )

    metadata_output.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\nHIGH PARKING OCCUPANCY CONFIGURATION")
    print("=" * 50)
    print(f"Seed: {seed}")
    print(f"Target occupancy: {target:.0%}")
    print(f"Physical capacity: {total_capacity}")
    print(f"Modeled occupied: {sum(occupied.values())}")
    print(f"Effective capacity: {total_capacity - sum(occupied.values())}")
    print(f"Parking file: {parking_output}")
    print(f"Metadata file: {metadata_output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=float, default=0.90)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    if not 0 <= args.target <= 1:
        parser.error("--target must be between 0 and 1")

    generate_occupancy(args.target, args.seed)
