import argparse
import copy
import random
import xml.etree.ElementTree as ET
from pathlib import Path

import sumolib

ROOT = Path(__file__).resolve().parents[3]

NETWORK = ROOT / "simulation/sumo/network/osm.net.xml.gz"

EXPERIMENTAL_DIR = (
    ROOT / "simulation/sumo/routes/scenarios/normal"
)

OUTPUT_DIR = (
    ROOT / "simulation/sumo/routes/scenarios"
)

ENTRY_EDGE_IDS = [
    "180618650#0",
    "405201550",
    "991195811",
]

EXIT_EDGE_IDS = [
    "180618649#1",
    "1001728056",
    "-1203960827#1",
]

MIN_ROUTE_DISTANCE = 500

SCENARIOS = {
    "low": 15,
    "normal": 29,
    "peak": 116,
}

MIN_ROUTE_EDGES = 5
DEPARTURE_JITTER = 8.0


def load_experimental_vehicles(seed):
    path = (
        EXPERIMENTAL_DIR /
        f"seed_{seed}_distributed.rou.xml"
    )

    root = ET.parse(path).getroot()

    vehicles = [
        copy.deepcopy(vehicle)
        for vehicle in root.findall("vehicle")
        if vehicle.get("id", "").startswith("parking_vehicle_")
    ]

    if len(vehicles) != 40:
        raise ValueError(
            f"Expected 40 experimental vehicles, found {len(vehicles)}"
        )

    definitions = [
        copy.deepcopy(child)
        for child in root
        if child.tag != "vehicle"
    ]

    return root, definitions, vehicles



def generate_route_pool(net):
    route_pool = []
    seen_routes = set()

    for origin_id in ENTRY_EDGE_IDS:
        origin = net.getEdge(origin_id)

        for destination_id in EXIT_EDGE_IDS:
            destination = net.getEdge(destination_id)

            route, distance = net.getShortestPath(
                origin,
                destination,
                vClass="passenger",
            )

            if not route:
                continue

            if distance < MIN_ROUTE_DISTANCE:
                continue

            route_ids = tuple(
                edge.getID()
                for edge in route
            )

            if route_ids in seen_routes:
                continue

            seen_routes.add(route_ids)
            route_pool.append(route_ids)

    if not route_pool:
        raise RuntimeError(
            "No valid background routes found."
        )

    print(
        f"Found {len(route_pool)} valid background routes"
    )

    return route_pool


def generate_departures(experimental, count, rng):
    departures = sorted(
        float(vehicle.get("depart"))
        for vehicle in experimental
    )

    # Spread background vehicles across the experimental
    # departure period, rather than spawning them at once.
    background_times = []

    for i in range(count):
        index = int(i * len(departures) / count)
        anchor = departures[index]

        jitter = rng.uniform(
            0,
            DEPARTURE_JITTER
        )

        background_times.append(anchor + jitter)

    return sorted(background_times)


def generate_scenario(name, seed, net, route_pool):
    rng = random.Random(seed)

    root, definitions, experimental = (
        load_experimental_vehicles(seed)
    )

    count = SCENARIOS[name]

    background_times = generate_departures(
        experimental,
        count,
        rng,
    )

    # Reuse routes only when necessary.
    selected_routes = []

    while len(selected_routes) < count:
        shuffled = route_pool[:]
        rng.shuffle(shuffled)
        selected_routes.extend(shuffled)

    selected_routes = selected_routes[:count]

    background = []

    for i, (depart, edges) in enumerate(
        zip(background_times, selected_routes)
    ):
        vehicle = ET.Element(
            "vehicle",
            {
                "id": f"background_vehicle_{i}",
                "type": "passenger_car",
                "depart": f"{depart:.2f}",
            },
        )

        ET.SubElement(
            vehicle,
            "route",
            {
                "edges": " ".join(edges)
            },
        )

        background.append(vehicle)

    all_vehicles = experimental + background

    all_vehicles.sort(
        key=lambda vehicle: float(
            vehicle.get("depart", "0")
        )
    )

    output_root = ET.Element(
        root.tag,
        root.attrib
    )

    output_root.extend(definitions)
    output_root.extend(all_vehicles)

    ET.indent(output_root, space="    ")

    output_dir = OUTPUT_DIR / name
    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_dir /
        f"seed_{seed}_traffic.rou.xml"
    )

    ET.ElementTree(output_root).write(
        output_file,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"\nScenario: {name}")
    print(f"Seed: {seed}")
    print(f"Experimental vehicles: {len(experimental)}")
    print(f"Background vehicles: {len(background)}")
    print(f"Available background routes: {len(route_pool)}")
    print(f"Total vehicles: {len(all_vehicles)}")
    print(f"Output: {output_file}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        choices=SCENARIOS.keys(),
        required=True
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42
    )

    args = parser.parse_args()

    print("Loading SUMO network...")
    net = sumolib.net.readNet(str(NETWORK))

    print("Generating background route pool...")
    route_pool = generate_route_pool(net)

    generate_scenario(
        args.scenario,
        args.seed,
        net,
        route_pool
    )


if __name__ == "__main__":
    main()
