
import argparse
import json
import random
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

import sumolib

ROOT = Path(__file__).resolve().parents[2]

NETWORK = ROOT / "simulation/sumo/network/osm.net.xml.gz"
PARKING = ROOT / "simulation/sumo/additionals/parking.add.xml"
PARKING_LOTS = ROOT / "shared/config/parking-lots.json"

OUTPUT = ROOT / "simulation/sumo/routes/test_parking.rou.xml"

ENTRY_EDGE_IDS = [
    "156927285",
    "180618650#0",
    "405201550",
    "406206827#0",
    "406465877",
    "44219693",
    "991195811",
]

PARKING_DURATION = 300
DEPARTURE_INTERVAL = 20


def load_parking_areas():
    root = ET.parse(PARKING).getroot()

    return {
        area.get("id"): area
        for area in root.findall(".//parkingArea")
    }


def find_reachable_destinations(net, parking_areas, lot_config):
    destinations = {}

    for lot_id, lot in lot_config["lots"].items():
        if not lot.get("enabled", True):
            continue

        candidates = []

        for area_id in lot["sumoParkingAreas"]:
            area = parking_areas.get(area_id)

            if area is None:
                continue

            capacity = int(area.get("roadsideCapacity", "0"))

            if capacity <= 0:
                continue

            try:
                lane = net.getLane(area.get("lane"))
                destination_edge = lane.getEdge()
            except (KeyError, AttributeError):
                continue

            if not destination_edge.allows("passenger"):
                continue

            for entry_id in ENTRY_EDGE_IDS:
                try:
                    entry_edge = net.getEdge(entry_id)
                except KeyError:
                    continue

                route, cost = net.getShortestPath(
                    entry_edge,
                    destination_edge,
                    vClass="passenger",
                )

                if route:
                    candidates.append({
                        "lot": lot_id,
                        "area": area_id,
                        "entry": entry_id,
                        "capacity": capacity,
                        "edges": [edge.getID() for edge in route],
                    })

        destinations[lot_id] = candidates

    return destinations


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--vehicles",
        type=int,
        default=40,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    if args.vehicles <= 0:
        parser.error("--vehicles must be greater than zero")

    rng = random.Random(args.seed)

    print("Loading SUMO network...")
    net = sumolib.net.readNet(str(NETWORK))

    parking_areas = load_parking_areas()

    with open(PARKING_LOTS, encoding="utf-8") as file:
        lot_config = json.load(file)

    destinations = find_reachable_destinations(
        net,
        parking_areas,
        lot_config,
    )

    lot_ids = sorted(destinations)

    if not lot_ids:
        raise RuntimeError("No enabled parking lots found")

    for lot_id in lot_ids:
        if not destinations[lot_id]:
            raise RuntimeError(
                f"No reachable parking areas in lot {lot_id}"
            )

    routes_root = ET.Element("routes")

    ET.SubElement(
        routes_root,
        "vType",
        {
            "id": "passenger_car",
            "vClass": "passenger",
            "accel": "2.6",
            "decel": "4.5",
            "length": "5",
            "minGap": "2.5",
            "maxSpeed": "13.9",
        },
    )

    # Assign vehicles evenly across enabled parking lots.
    vehicle_lots = [
        lot_ids[i % len(lot_ids)]
        for i in range(args.vehicles)
    ]

    rng.shuffle(vehicle_lots)

    # Track assigned vehicles by parking area.
    # Conservative capacity check: assume parking periods overlap.
    assigned = Counter()
    lot_counts = Counter()

    for i, lot_id in enumerate(vehicle_lots):
        # Shuffle candidates to vary entrances and destinations.
        candidates = destinations[lot_id][:]
        rng.shuffle(candidates)

        selected = next(
            (
                candidate
                for candidate in candidates
                if assigned[candidate["area"]] < candidate["capacity"]
            ),
            None,
        )

        if selected is None:
            raise RuntimeError(
                f"Not enough reachable parking capacity in lot {lot_id}"
            )

        area_id = selected["area"]
        assigned[area_id] += 1
        lot_counts[lot_id] += 1

        route_id = f"route_{i}"

        ET.SubElement(
            routes_root,
            "route",
            {
                "id": route_id,
                "edges": " ".join(selected["edges"]),
            },
        )

        vehicle = ET.SubElement(
            routes_root,
            "vehicle",
            {
                "id": f"parking_vehicle_{i}",
                "type": "passenger_car",
                "route": route_id,
                "depart": str(i * DEPARTURE_INTERVAL),
            },
        )

        ET.SubElement(
            vehicle,
            "stop",
            {
                "parkingArea": area_id,
                "duration": str(PARKING_DURATION),
            },
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    ET.indent(routes_root, space="    ")

    ET.ElementTree(routes_root).write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"\nGenerated {args.vehicles} vehicles")
    print(f"Random seed: {args.seed}")

    for lot_id in lot_ids:
        print(f"Lot {lot_id}: {lot_counts[lot_id]} vehicles")

    print(f"\nSaved to: {OUTPUT}")


if __name__ == "__main__":
    main()
