import argparse
import math
import sys
import xml.etree.ElementTree as ET

from collections import Counter
from functools import lru_cache
from pathlib import Path

import sumolib
import traci


ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(ROOT / "simulation/src"))

from campus_destinations import get_destination_coordinates


NETWORK_FILE = ROOT / "simulation/sumo/network/osm.net.xml.gz"

PARKING_FILE = ROOT / "simulation/sumo/additionals/parking.add.xml"

SUMO_CONFIG = ROOT / "simulation/sumo/config/campus.sumocfg"

ROUTE_DIR = ROOT / "simulation/sumo/routes/scenarios"

SCENARIOS = ("low", "normal", "peak")

SEEDS = (42, 43, 44, 45, 46)

EXPECTED_BACKGROUND = {
    "low": 15,
    "normal": 29,
    "peak": 116,
}


def load_parking_inventory(net):
    """
    Retrieve resolved parking geometry from SUMO.

    Physical capacity is used only to establish whether
    a parking area is a valid candidate.
    """

    parking_root = ET.parse(PARKING_FILE).getroot()

    physical_capacities = {
        area.get("id"): int(area.get("roadsideCapacity", "0"))
        for area in parking_root.iter("parkingArea")
    }

    inventory = []

    traci.start([
        "sumo",
        "-c", str(SUMO_CONFIG),
        "--route-files",
        str(
            ROUTE_DIR /
            "normal/seed_42_traffic.rou.xml"
        ),
        "--additional-files", str(PARKING_FILE),
        "--time-to-teleport", "-1",
    ])

    try:
        for area_id in sorted(traci.parkingarea.getIDList()):

            capacity = physical_capacities.get(area_id, 0)

            if capacity <= 0:
                continue

            lane_id = traci.parkingarea.getLaneID(area_id)

            lane = net.getLane(lane_id)

            if not lane.allows("passenger"):
                continue

            start_pos = traci.parkingarea.getStartPos(area_id)
            end_pos = traci.parkingarea.getEndPos(area_id)

            midpoint = (start_pos + end_pos) / 2

            edge_id, lane_index = lane_id.rsplit("_", 1)

            coordinates = traci.simulation.convert2D(
                edge_id,
                midpoint,
                laneIndex=int(lane_index),
            )

            inventory.append({
                "id": area_id,
                "lane": lane_id,
                "edge": edge_id,
                "capacity": capacity,
                "coordinates": coordinates,
            })

    finally:
        traci.close()

    if not inventory:
        raise RuntimeError("No eligible parking areas found")

    print(
        f"Loaded {len(inventory)} eligible physical parking areas"
    )

    return inventory


def get_vehicle_destination(vehicle):
    for param in vehicle.findall("param"):
        if param.get("key") == "destination_building":
            return param.get("value")

    raise ValueError(
        f"Missing destination for {vehicle.get('id')}"
    )


def get_vehicle_route(vehicle, routes):
    route_id = vehicle.get("route")

    if route_id is not None:
        return routes[route_id].get("edges").split()

    inline_route = vehicle.find("route")

    if inline_route is None:
        raise ValueError(
            f"Missing route for {vehicle.get('id')}"
        )

    return inline_route.get("edges").split()


def create_route_finder(net):

    @lru_cache(maxsize=None)
    def shortest_path(origin_id, destination_id):

        route, distance = net.getShortestPath(
            net.getEdge(origin_id),
            net.getEdge(destination_id),
            vClass="passenger",
        )

        if not route:
            return None

        return tuple(edge.getID() for edge in route)

    return shortest_path


def select_closest_feasible_area(
    destination_xy,
    entry_edge,
    exit_edge,
    inventory,
    shortest_path,
):
    """
    Rank parking areas by walking distance.

    Select the closest area with valid outbound
    and return routes.
    """

    ranked_areas = sorted(
        inventory,
        key=lambda area: (
            math.dist(
                area["coordinates"],
                destination_xy,
            ),
            area["id"],
        ),
    )

    for area in ranked_areas:

        outbound = shortest_path(
            entry_edge,
            area["edge"],
        )

        if outbound is None:
            continue

        return_route = shortest_path(
            area["edge"],
            exit_edge,
        )

        if return_route is None:
            continue

        combined_edges = (
            outbound + return_route[1:]
        )

        walking_distance = math.dist(
            area["coordinates"],
            destination_xy,
        )

        return area, combined_edges, walking_distance

    raise RuntimeError(
        f"No feasible parking area for "
        f"{entry_edge} -> {exit_edge}"
    )


def generate_scenario(
    scenario,
    seed,
    inventory,
    shortest_path,
    overwrite=False,
):

    source = (
        ROUTE_DIR /
        scenario /
        f"seed_{seed}_traffic.rou.xml"
    )

    output = (
        ROUTE_DIR /
        scenario /
        f"seed_{seed}_destination_informed.rou.xml"
    )

    if not source.is_file():
        raise FileNotFoundError(source)

    if output.exists() and not overwrite:
        raise FileExistsError(
            f"{output} already exists. "
            "Use --overwrite to replace it."
        )

    tree = ET.parse(source)
    root = tree.getroot()

    routes = {
        route.get("id"): route
        for route in root.findall("route")
    }

    parking_vehicles = [
        vehicle
        for vehicle in root.findall("vehicle")
        if vehicle.get("id", "").startswith(
            "parking_vehicle_"
        )
    ]

    background_vehicles = [
        vehicle
        for vehicle in root.findall("vehicle")
        if vehicle.get("id", "").startswith(
            "background_vehicle_"
        )
    ]

    if len(parking_vehicles) != 40:
        raise ValueError(
            f"Expected 40 parking vehicles, "
            f"found {len(parking_vehicles)}"
        )

    if len(background_vehicles) != EXPECTED_BACKGROUND[scenario]:
        raise ValueError(
            "Unexpected background vehicle count"
        )

    inventory_by_id = {
        area["id"]: area
        for area in inventory
    }

    preferences = Counter()
    destinations = Counter()

    original_distances = []
    new_distances = []

    changed = 0
    new_routes = []

    for vehicle in parking_vehicles:

        vehicle_id = vehicle.get("id")

        original_edges = get_vehicle_route(
            vehicle,
            routes,
        )

        entry_edge = original_edges[0]
        exit_edge = original_edges[-1]

        destination = get_vehicle_destination(vehicle)

        destination_xy = get_destination_coordinates(
            destination
        )

        destinations[destination] += 1

        stop = vehicle.find("stop")

        if stop is None:
            raise ValueError(
                f"Missing parking stop for {vehicle_id}"
            )

        original_area_id = stop.get("parkingArea")

        if original_area_id not in inventory_by_id:
            raise ValueError(
                f"Original parking area unavailable "
                f"in physical inventory: {original_area_id}"
            )

        original_area = inventory_by_id[original_area_id]

        original_distance = math.dist(
            original_area["coordinates"],
            destination_xy,
        )

        area, edges, walking_distance = (
            select_closest_feasible_area(
                destination_xy,
                entry_edge,
                exit_edge,
                inventory,
                shortest_path,
            )
        )

        selected_area_id = area["id"]

        if selected_area_id != original_area_id:
            changed += 1

        if edges[0] != entry_edge:
            raise ValueError("Vehicle entrance changed")

        if edges[-1] != exit_edge:
            raise ValueError("Vehicle exit changed")

        if area["edge"] not in edges:
            raise ValueError(
                "Parking edge missing from reconstructed route"
            )

        new_route_id = (
            f"destination_informed_{vehicle_id}"
        )

        if new_route_id in routes:
            raise ValueError(
                f"Duplicate route ID: {new_route_id}"
            )

        new_route = ET.Element(
            "route",
            {
                "id": new_route_id,
                "edges": " ".join(edges),
            },
        )

        new_routes.append(new_route)

        inline_route = vehicle.find("route")

        if inline_route is not None:
            vehicle.remove(inline_route)

        vehicle.set("route", new_route_id)

        stop.set("parkingArea", selected_area_id)

        preferences[selected_area_id] += 1

        original_distances.append(original_distance)
        new_distances.append(walking_distance)

        print(
            f"{vehicle_id:22s} | "
            f"{destination:24s} | "
            f"{original_area_id:20s} -> "
            f"{selected_area_id:20s} | "
            f"{original_distance:7.2f}m -> "
            f"{walking_distance:7.2f}m"
        )

    # SUMO route definitions must precede vehicles
    # that reference them.

    definitions = [
        child
        for child in root
        if child.tag != "vehicle"
    ]

    vehicles = [
        child
        for child in root
        if child.tag == "vehicle"
    ]

    vehicles.sort(
        key=lambda vehicle: float(
            vehicle.get("depart", "0")
        )
    )

    root[:] = definitions + new_routes + vehicles

    ET.indent(root, space="    ")

    tree.write(
        output,
        encoding="utf-8",
        xml_declaration=True,
    )

    original_mean = (
        sum(original_distances) /
        len(original_distances)
    )

    new_mean = (
        sum(new_distances) /
        len(new_distances)
    )

    print("\n" + "=" * 65)
    print("DESTINATION-INFORMED ROUTE SUMMARY")
    print("=" * 65)

    print(f"Scenario: {scenario}")
    print(f"Seed: {seed}")
    print(f"Parking vehicles: {len(parking_vehicles)}")
    print(f"Background vehicles: {len(background_vehicles)}")
    print(f"Changed preferences: {changed}/40")
    print(f"Unique preferred areas: {len(preferences)}")

    print(
        f"Original mean preferred walking distance: "
        f"{original_mean:.2f} m"
    )

    print(
        f"New mean preferred walking distance: "
        f"{new_mean:.2f} m"
    )

    if original_mean > 0:
        reduction = (
            (original_mean - new_mean) /
            original_mean
        ) * 100

        print(
            f"Preferred walking distance reduction: "
            f"{reduction:.2f}%"
        )

    print("\nDESTINATION DISTRIBUTION")

    for destination, count in sorted(destinations.items()):
        print(f"  {destination:25s}: {count}")

    print("\nPREFERRED PARKING AREA DISTRIBUTION")

    for area_id, count in preferences.most_common():

        capacity = inventory_by_id[area_id]["capacity"]

        print(
            f"  {area_id:25s} | "
            f"vehicles={count:2d} | "
            f"physical capacity={capacity}"
        )

    print(f"\nOutput: {output}")


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate destination-informed parking routes"
        )
    )

    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        required=True,
    )

    parser.add_argument(
        "--seed",
        type=int,
        choices=SEEDS,
        default=42,
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    args = parser.parse_args()

    print("Loading SUMO network...")

    net = sumolib.net.readNet(str(NETWORK_FILE))

    print("Loading physical parking inventory...")

    inventory = load_parking_inventory(net)

    shortest_path = create_route_finder(net)

    generate_scenario(
        args.scenario,
        args.seed,
        inventory,
        shortest_path,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()