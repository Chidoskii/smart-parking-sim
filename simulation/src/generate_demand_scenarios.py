import argparse
import copy
import random
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCE = (
    ROOT / "simulation/sumo/routes/"
    "combined_parking_roundtrip.rou.xml"
)

OUTPUT_DIR = (
    ROOT / "simulation/sumo/routes/scenarios"
)

# Initial experimental configurations.
# Background vehicle counts only; the 40 experimental
# parking vehicles remain unchanged.
SCENARIOS = {
    "low": {
        "background_count": 15,
        "depart_start": 0,
        "depart_end": 1380,
    },
    "normal": {
        "background_count": 29,
        "depart_start": None,
        "depart_end": None,
    },
    "peak": {
        "background_count": 116,
        "depart_start": 600,
        "depart_end": 900,
    },
}


def generate_scenario(name, seed):
    config = SCENARIOS[name]
    rng = random.Random(seed)

    root = ET.parse(SOURCE).getroot()

    experimental = [
        vehicle
        for vehicle in root.findall("vehicle")
        if vehicle.get("id", "").startswith("parking_vehicle_")
    ]

    background = [
        vehicle
        for vehicle in root.findall("vehicle")
        if vehicle.get("id", "").startswith("background_vehicle_")
    ]

    if len(experimental) != 40:
        raise ValueError(
            f"Expected 40 experimental vehicles, "
            f"found {len(experimental)}"
        )

    if not background:
        raise ValueError("No background vehicles found")

    # Remove original background vehicles.
    for vehicle in background:
        root.remove(vehicle)

    count = config["background_count"]

    if name == "normal":
        # Preserve original departure times and vehicle IDs.
        new_background = [
            copy.deepcopy(vehicle)
            for vehicle in background
        ]

        if len(new_background) != count:
            raise ValueError(
                f"Normal scenario expects {count} background "
                f"vehicles, found {len(new_background)}"
            )

    else:
        new_background = []

        templates = [
            background[i % len(background)]
            for i in range(count)
        ]

        start = config["depart_start"]
        end = config["depart_end"]

        departure_times = sorted(
            rng.uniform(start, end)
            for _ in range(count)
        )

        for i, (template, depart) in enumerate(
            zip(templates, departure_times)
        ):
            vehicle = copy.deepcopy(template)

            vehicle.set("id", f"background_vehicle_{i}")
            vehicle.set("depart", f"{depart:.2f}")

            new_background.append(vehicle)

    # Background traffic should not occupy parking spaces.
    # Vehicles follow their routes and exit the network.
    removed_stops = 0

    for vehicle in new_background:
        for stop in list(vehicle.findall("stop")):
            vehicle.remove(stop)
            removed_stops += 1

        root.append(vehicle)

    # Ensure route definitions precede vehicles and
    # vehicles are sorted by departure time.
    definitions = [
        child for child in root
        if child.tag != "vehicle"
    ]

    vehicles = [
        child for child in root
        if child.tag == "vehicle"
    ]

    vehicles.sort(
        key=lambda vehicle: float(
            vehicle.get("depart", "0")
        )
    )

    root[:] = definitions + vehicles

    ET.indent(root, space="    ")

    output_dir = OUTPUT_DIR / name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"seed_{seed}.rou.xml"

    ET.ElementTree(root).write(
        output_file,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"\nScenario: {name}")
    print(f"Seed: {seed}")
    print(f"Experimental vehicles: {len(experimental)}")
    print(f"Background vehicles: {len(new_background)}")
    print(f"Background stops removed: {removed_stops}")
    print(f"Total vehicles: {len(experimental) + len(new_background)}")
    print(f"Output: {output_file}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        choices=SCENARIOS.keys(),
        required=True,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    generate_scenario(args.scenario, args.seed)


if __name__ == "__main__":
    main()
