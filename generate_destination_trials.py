import argparse
import copy
import random
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ROUTE_DIR = (
    ROOT / "simulation/sumo/routes/scenarios/normal"
)

SOURCE = ROUTE_DIR / "seed_42_distributed.rou.xml"

DESTINATIONS = {
    "college_of_science",
    "college_of_engineering",
    "college_of_business",
    "university_library",
    "bronco_student_center",
}


def destination_of(vehicle):
    for param in vehicle.findall("param"):
        if param.get("key") == "destination_building":
            return param.get("value")
    return None


def validate_source(root):
    vehicles = [
        vehicle
        for vehicle in root.findall("vehicle")
        if vehicle.get("id", "").startswith("parking_vehicle_")
    ]

    if len(vehicles) != 40:
        raise ValueError(
            f"Expected 40 vehicles, found {len(vehicles)}"
        )

    counts = Counter(destination_of(v) for v in vehicles)

    if set(counts) != DESTINATIONS or any(
        counts[d] != 8 for d in DESTINATIONS
    ):
        raise ValueError(
            f"Unexpected destination distribution: {counts}"
        )

    departures = sorted(
        float(vehicle.get("depart"))
        for vehicle in vehicles
    )

    expected = [float(i * 20) for i in range(40)]

    if departures != expected:
        raise ValueError("Unexpected departure schedule")

    for vehicle in vehicles:
        if vehicle.find("stop") is None:
            raise ValueError(
                f"Missing parking stop: {vehicle.get('id')}"
            )

    return vehicles, departures


def generate(seed, overwrite=False):
    output = (
        ROUTE_DIR / f"seed_{seed}_distributed.rou.xml"
    )

    if output.exists() and not overwrite:
        raise FileExistsError(
            f"{output} already exists. "
            "Use --overwrite to replace it."
        )

    root = copy.deepcopy(ET.parse(SOURCE).getroot())

    vehicles, departure_slots = validate_source(root)

    rng = random.Random(seed)

    shuffled_slots = departure_slots[:]
    rng.shuffle(shuffled_slots)

    for vehicle, depart in zip(vehicles, shuffled_slots):
        vehicle.set("depart", f"{depart:g}")

    # SUMO requires chronological vehicle ordering.
    definitions = [
        child for child in root
        if child.tag != "vehicle"
    ]

    all_vehicles = [
        child for child in root
        if child.tag == "vehicle"
    ]

    all_vehicles.sort(
        key=lambda vehicle: float(
            vehicle.get("depart", "0")
        )
    )

    root[:] = definitions + all_vehicles

    # Validate the generated file before writing.
    validate_source(root)

    ET.indent(root, space="    ")

    ROUTE_DIR.mkdir(parents=True, exist_ok=True)

    ET.ElementTree(root).write(
        output,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"Generated: {output}")
    print(f"  Vehicles: {len(vehicles)}")
    print(f"  Destinations: {dict(Counter(destination_of(v) for v in vehicles))}")
    print("  Routes and parking preferences: preserved")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[43, 44, 45, 46],
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    args = parser.parse_args()

    for seed in args.seeds:
        if seed == 42:
            raise ValueError(
                "Seed 42 is the source and must not be overwritten"
            )

        generate(seed, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
