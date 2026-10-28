import csv
import json
import time
import sumolib
import argparse
import xml.etree.ElementTree as ET

from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError
try:
    from .parking_policies import get_parking_policy
except ImportError:
    from parking_policies import get_parking_policy

import traci

ROOT = Path(__file__).resolve().parents[2]

SUMO_CONFIG = (
    ROOT / "simulation/sumo/config/campus.sumocfg"
)

ROUTES_FILE = ROOT / "simulation/sumo/routes/test_parking.rou.xml"
NETWORK_FILE = ROOT / "simulation/sumo/network/osm.net.xml.gz"
PARKING_FILE = ROOT / "simulation/sumo/additionals/parking.add.xml"

PARKING_SEARCH_DISTANCE_M = 200.0

RESULTS_DIR = ROOT / "simulation/results"

SCENARIOS = ("baseline", "availability", "smart")


def create_run_directory(scenario):
    scenario_dir = RESULTS_DIR / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)

    run_number = 1

    while True:
        run_dir = scenario_dir / f"run_{run_number:03d}"

        try:
            run_dir.mkdir(exist_ok=False)
            return run_dir
        except FileExistsError:
            run_number += 1

BACKEND_URL = "http://localhost:5000"

SIMULATION_STEPS = 4800
OCCUPANCY_UPDATE_INTERVAL = 5
VEHICLE_UPDATE_INTERVAL = 1
GASOLINE_DENSITY_G_PER_L = 745.0
LITERS_PER_US_GALLON = 3.785411784
METERS_PER_MILE = 1609.344

# Delay between simulation steps so the dashboard
# can display occupancy changes.
STEP_DELAY = 0.01


def update_backend(area_id, occupied):
    encoded_area_id = quote(area_id, safe="")

    url = (
        f"{BACKEND_URL}/api/occupancy/areas/"
        f"{encoded_area_id}"
    )

    payload = json.dumps({
        "occupied": occupied
    }).encode("utf-8")

    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="PATCH"
    )

    try:
        with urlopen(request, timeout=5) as response:
            return json.load(response)

    except (HTTPError, URLError) as error:
        print(f"Backend update failed for {area_id}: {error}")
        return None

def update_vehicle_positions(vehicles):
    url = f"{BACKEND_URL}/api/vehicles/positions"

    payload = json.dumps({
        "vehicles": vehicles
    }).encode("utf-8")

    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urlopen(request, timeout=5) as response:
            return json.load(response)

    except (HTTPError, URLError) as error:
        print(f"Vehicle position update failed: {error}")
        return None

def get_vehicle_positions():
    vehicles = []

    for vehicle_id in traci.vehicle.getIDList():
        x, y = traci.vehicle.getPosition(vehicle_id)

        # Convert SUMO coordinates to longitude/latitude.
        longitude, latitude = traci.simulation.convertGeo(x, y)

        vehicles.append({
            "id": vehicle_id,
            "longitude": longitude,
            "latitude": latitude,
            "speed": traci.vehicle.getSpeed(vehicle_id),
            "angle": traci.vehicle.getAngle(vehicle_id),
            "roadId": traci.vehicle.getRoadID(vehicle_id),
        })

    return vehicles

def load_vehicle_assignments(route_file):
    root = ET.parse(route_file).getroot()
    assignments = {}

    for vehicle in root.findall("vehicle"):
        vehicle_id = vehicle.get("id")

        if not vehicle_id.startswith("parking_vehicle_"):
            continue
        stop = vehicle.find("stop")

        if stop is None:
            continue

        preferred_area = stop.get("parkingArea")

        if not preferred_area:
            continue

        assignments[vehicle_id] = {
            "preferred_parking_area": preferred_area,
            "assigned_parking_area": preferred_area,
        }

    return assignments

def load_search_boundaries(route_file):
    """
    Calculate a fixed search-start boundary for every vehicle.

    The boundary is 200 meters of route distance before the
    entrance to the vehicle's originally preferred parking area.
    """

    net = sumolib.net.readNet(str(NETWORK_FILE))

    routes_root = ET.parse(route_file).getroot()
    parking_root = ET.parse(PARKING_FILE).getroot()

    routes = {
        route.get("id"): route.get("edges").split()
        for route in routes_root.findall("route")
    }

    parking_areas = {
        area.get("id"): area
        for area in parking_root.findall("parkingArea")
    }

    boundaries = {}

    for vehicle in routes_root.findall("vehicle"):
        vehicle_id = vehicle.get("id")
        
        if not vehicle_id.startswith("parking_vehicle_"):
            continue
        stop = vehicle.find("stop")

        if stop is None:
            continue

        area_id = stop.get("parkingArea")

        if not area_id:
            continue

        area = parking_areas[area_id]

        route_id = vehicle.get("route")

        if route_id is not None:
            edges = routes[route_id]
        else:
            inline_route = vehicle.find("route")
            if inline_route is None:
                raise ValueError(f"No route for {vehicle_id}")
            edges = inline_route.get("edges").split()

        parking_lane = area.get("lane")
        parking_edge = parking_lane.rsplit("_", 1)[0]
        parking_position = float(area.get("startPos", "0.0"))

        # Find the final occurrence of the preferred parking edge.
        parking_index = next(
            (
                i for i in range(len(edges) - 1, -1, -1)
                if edges[i] == parking_edge
            ),
            None
        )

        if parking_index is None:
            raise ValueError(
                f"{vehicle_id}: parking edge {parking_edge} "
                "not found in original route"
            )

        remaining = PARKING_SEARCH_DISTANCE_M

        boundary = None

        for index in range(parking_index, -1, -1):
            edge_id = edges[index]
            edge = net.getEdge(edge_id)

            if index == parking_index:
                usable_length = parking_position
            else:
                usable_length = edge.getLength()

            if remaining <= usable_length:
                boundary = {
                    "edge": edge_id,
                    "position": usable_length - remaining,
                    "route_index": index,
                }
                break

            remaining -= usable_length

        # If the route is shorter than 200 meters,
        # begin measuring at departure.
        if boundary is None:
            boundary = {
                "edge": edges[0],
                "position": 0.0,
                "route_index": 0,
            }

        boundaries[vehicle_id] = boundary

    return boundaries

def save_vehicle_metrics(vehicle_metrics, run_dir):
    vehicle_results = run_dir / "vehicle_metrics.csv"

    fieldnames = [
        "vehicle_id",
        "preferred_parking_area",
        "assigned_parking_area",
        "departure_time",
        "parking_arrival_time",
        "time_to_parking",
        "search_start_time",
        "parking_search_time",
        "waiting_time",
        "time_loss",
        "parking_success",
        "parking_reassignments",
        "teleported",
        "co2_g",
        "fuel_g",
        "fuel_gallons",
        "distance_m",
        "distance_miles",
    ]

    with open(
        vehicle_results,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(vehicle_metrics.values())

    successful = sum(
        1
        for metrics in vehicle_metrics.values()
        if metrics["parking_success"]
    )

    print(f"\nVehicle metrics saved to: {vehicle_results}")
    print(f"Successfully parked: {successful}/{len(vehicle_metrics)}")

def get_parking_area_inventory():
    parking_file = ROOT / "simulation/sumo/additionals/parking.add.xml"
    root = ET.parse(parking_file).getroot()

    capacities = {
        area.get("id"): int(area.get("roadsideCapacity"))
        for area in root.findall("parkingArea")
    }

    inventory = []

    for area_id in traci.parkingarea.getIDList():
        capacity = capacities[area_id]
        occupied = traci.parkingarea.getVehicleCount(area_id)

        inventory.append({
            "id": area_id,
            "capacity": capacity,
            "occupied": occupied,
            "available": max(0, capacity - occupied),
        })

    return inventory

def get_reachable_parking_candidates(vehicle_id, inventory, reservations):
    candidates = []

    for area in inventory:
        area_id = area["id"]

        effective_occupancy = (
            area["occupied"] + reservations.get(area_id, 0)
        )

        if effective_occupancy >= area["capacity"]:
            continue

        lane_id = traci.parkingarea.getLaneID(area_id)
        edge_id = lane_id.rsplit("_", 1)[0]

        try:
            route = traci.simulation.findRoute(
                traci.vehicle.getRoadID(vehicle_id),
                edge_id,
                vType=traci.vehicle.getTypeID(vehicle_id),
            )
        except traci.TraCIException:
            continue

        if not route.edges:
            continue

        candidates.append({
            "id": area_id,
            "capacity": area["capacity"],
            "distance": route.length,
        })

    return candidates


def get_pending_reservations(vehicle_metrics):
    """
    Count experimental vehicles that have departed,
    have an assigned parking area, and have not parked yet.
    """
    reservations = {}

    for metrics in vehicle_metrics.values():
        if metrics["departure_time"] is None:
            continue

        if metrics["parking_success"]:
            continue

        area_id = metrics["assigned_parking_area"]

        if area_id is None:
            continue

        reservations[area_id] = reservations.get(area_id, 0) + 1

    return reservations


def main():
    parser = argparse.ArgumentParser(
        description="Run the smart parking SUMO simulation."
    )

    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="baseline",
        help="Experiment scenario name."
    )

    parser.add_argument(
        "--route-file",
        type=Path,
        default=ROUTES_FILE,
        help="SUMO route file to use for this simulation."
    )

    args = parser.parse_args()

    route_file = args.route_file.resolve()

    if not route_file.is_file():
        parser.error(f"Route file not found: {route_file}")

    scenario = args.scenario

    policy = get_parking_policy(scenario)

    print(f"Selected parking policy: {type(policy).__name__}")

    print("Starting SUMO-to-backend bridge...")
    print(f"Scenario: {scenario}")

    # Verify the backend is available before starting SUMO.
    try:
        with urlopen(
            f"{BACKEND_URL}/api/occupancy",
            timeout=5
        ) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Backend returned HTTP {response.status}"
                )
    except URLError as error:
        raise RuntimeError(
            "Cannot connect to Express backend. "
            "Start it before running this script."
        ) from error

    traci.start([
        "sumo",
        "-c",
        str(SUMO_CONFIG),
        "--route-files",
        str(route_file),
    ])

    try:
        parking_areas = traci.parkingarea.getIDList()
        parking_inventory = get_parking_area_inventory()

        total_capacity = sum(
            area["capacity"] for area in parking_inventory
        )

        total_occupied = sum(
            area["occupied"] for area in parking_inventory
        )

        print(f"Total parking capacity: {total_capacity}")
        print(f"Initially occupied spaces: {total_occupied}")
        print(f"Initially available spaces: {total_capacity - total_occupied}")

        assignments = load_vehicle_assignments(route_file)
        search_boundaries = load_search_boundaries(route_file)

        print(f"Calculated search boundaries for {len(search_boundaries)} vehicles")

        vehicle_metrics = {}

        for vehicle_id, assignment in assignments.items():
            vehicle_metrics[vehicle_id] = {
                "vehicle_id": vehicle_id,
                "preferred_parking_area": assignment["preferred_parking_area"],
                "assigned_parking_area": assignment["assigned_parking_area"],
                "departure_time": None,
                "parking_arrival_time": None,
                "time_to_parking": None,
                "search_start_time": None,
                "parking_search_time": None,
                "waiting_time": None,
                "time_loss": None,
                "parking_success": False,
                "parking_reassignments": 0,
                "teleported": False,
                "co2_g": 0.0,
                "fuel_g": 0.0,
                "fuel_gallons": 0.0,
                "distance_m": 0.0,
                "distance_miles": 0.0,
            }

        print(f"Connected to {len(parking_areas)} parking areas")

        # Store the last occupancy successfully sent.
        # Synchronize the backend with SUMO's initial parking occupancy.
        last_occupancy = {}

        print("Synchronizing initial parking occupancy...")

        for area_id in parking_areas:
            occupied = traci.parkingarea.getVehicleCount(area_id)

            result = update_backend(area_id, occupied)

            if result is not None:
                last_occupancy[area_id] = occupied

        print(
            f"Initialized occupancy for "
            f"{len(last_occupancy)}/{len(parking_areas)} parking areas"
        )

        for step in range(SIMULATION_STEPS):
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            for vehicle_id in traci.simulation.getStartingTeleportIDList():
                if vehicle_id in vehicle_metrics:
                    vehicle_metrics[vehicle_id]["teleported"] = True
                    print(
                        f"TELEPORT: {vehicle_id} "
                        f"at simulation time {current_time:.0f}s"
                    )
            # Record actual vehicle departures.
            for vehicle_id in traci.simulation.getDepartedIDList():
                if vehicle_id in vehicle_metrics:
                    vehicle_metrics[vehicle_id]["departure_time"] = current_time
            # Detect when vehicles enter their original parking search zone.
            active_vehicle_ids = set(traci.vehicle.getIDList())

            for vehicle_id, metrics in vehicle_metrics.items():
                if metrics["departure_time"] is None:
                    continue

                if metrics["parking_success"]:
                    continue

                if metrics["search_start_time"] is not None:
                    continue

                if vehicle_id not in active_vehicle_ids:
                    continue

                boundary = search_boundaries.get(vehicle_id)

                if boundary is None:
                    continue

                current_route_index = traci.vehicle.getRouteIndex(vehicle_id)
                current_edge = traci.vehicle.getRoadID(vehicle_id)
                current_position = traci.vehicle.getLanePosition(vehicle_id)

                if (
                    current_route_index > boundary["route_index"]
                    or (
                        current_route_index == boundary["route_index"]
                        and current_edge == boundary["edge"]
                        and current_position >= boundary["position"]
                    )
                ):
                    metrics["search_start_time"] = current_time
                    if scenario == "availability":
                        inventory = get_parking_area_inventory()
                        reservations = get_pending_reservations(vehicle_metrics)

                        preferred_area = metrics["assigned_parking_area"]

                        reservations[preferred_area] = max(
                            0,
                            reservations.get(preferred_area, 0) - 1,
                        )

                        occupancy = {
                            area["id"]: (
                                area["occupied"]
                                + reservations.get(area["id"], 0)
                            )
                            for area in inventory
                        }

                        preferred_info = next(
                            (area for area in inventory if area["id"] == preferred_area),
                            None,
                        )

                        if preferred_info is None:
                            print(
                                f"WARNING: Unknown parking area "
                                f"{preferred_area} for {vehicle_id}"
                            )

                        elif occupancy[preferred_area] >= preferred_info["capacity"]:
                            candidates = get_reachable_parking_candidates(
                                vehicle_id,
                                inventory,
                                reservations,
                            )

                            selected_area = policy.select_parking_area(
                                vehicle_id=vehicle_id,
                                destination=preferred_area,
                                parking_areas=candidates,
                                occupancy=occupancy,
                            )

                            if selected_area is not None and selected_area != preferred_area:
                                try:
                                    traci.vehicle.rerouteParkingArea(
                                        vehicle_id,
                                        selected_area,
                                    )

                                    metrics["assigned_parking_area"] = selected_area
                                    metrics["parking_reassignments"] += 1

                                    print(
                                        f"REASSIGNED: {vehicle_id} "
                                        f"{preferred_area} -> {selected_area} "
                                        f"at time {current_time:.0f}s"
                                    )

                                except traci.TraCIException as error:
                                    print(
                                        f"REASSIGNMENT FAILED: "
                                        f"{vehicle_id}: {error}"
                                    )

                            else:
                                print(
                                    f"NO AVAILABLE ALTERNATIVE: "
                                    f"{vehicle_id} at time {current_time:.0f}s"
                                )
            # Collect emissions and distance before parking.
            # SUMO CO2 and fuel consumption getters return rates in mg/s.
            step_length = traci.simulation.getDeltaT()

            for vehicle_id, metrics in vehicle_metrics.items():
                if metrics["departure_time"] is None:
                    continue

                if metrics["parking_success"]:
                    continue

                if vehicle_id not in traci.vehicle.getIDList():
                    continue

                co2_mg_s = traci.vehicle.getCO2Emission(vehicle_id)
                fuel_mg_s = traci.vehicle.getFuelConsumption(vehicle_id)

                metrics["co2_g"] += (co2_mg_s * step_length) / 1000.0
                metrics["fuel_g"] += (fuel_mg_s * step_length) / 1000.0
                metrics["fuel_gallons"] = (metrics["fuel_g"] / GASOLINE_DENSITY_G_PER_L / LITERS_PER_US_GALLON)

                # Record current cumulative vehicle distance.
                metrics["distance_m"] = traci.vehicle.getDistance(vehicle_id)
                metrics["distance_miles"] = (metrics["distance_m"] / METERS_PER_MILE)

            # Check which vehicles are currently parked.
            for area_id in parking_areas:
                parked_vehicles = traci.parkingarea.getVehicleIDs(area_id)

                for vehicle_id in parked_vehicles:
                    if vehicle_id not in vehicle_metrics:
                        continue

                    metrics = vehicle_metrics[vehicle_id]

                    # Only record the first arrival at the assigned area.
                    if (
                        metrics["parking_arrival_time"] is None
                        and metrics["assigned_parking_area"] == area_id
                    ):
                        metrics["parking_arrival_time"] = current_time
                        metrics["parking_success"] = True

                        departure = metrics["departure_time"]

                        if departure is not None:
                            metrics["time_to_parking"] = (
                                current_time - departure
                            )

                        search_start = metrics["search_start_time"]

                        if search_start is not None:
                            metrics["parking_search_time"] = (
                                current_time - search_start
                            )

                        # Capture waiting time and time loss at arrival.
                        metrics["waiting_time"] = (
                            traci.vehicle.getAccumulatedWaitingTime(vehicle_id)
                        )

                        metrics["time_loss"] = (
                            traci.vehicle.getTimeLoss(vehicle_id)
                        )

            if step % OCCUPANCY_UPDATE_INTERVAL == 0:
                for area_id in parking_areas:
                    occupied = traci.parkingarea.getVehicleCount(
                        area_id
                    )

                    # Only send an update if occupancy changed.
                    if last_occupancy.get(area_id) == occupied:
                        continue

                    result = update_backend(area_id, occupied)

                    if result is not None:
                        last_occupancy[area_id] = occupied

                        print(
                            f"Time {traci.simulation.getTime():.0f}s | "
                            f"{area_id}: {occupied} occupied"
                        )

            if step % VEHICLE_UPDATE_INTERVAL == 0:
                vehicles = get_vehicle_positions()
                update_vehicle_positions(vehicles)        

            time.sleep(STEP_DELAY)
            if traci.simulation.getMinExpectedNumber() == 0:
                print("\nAll vehicles have completed their routes.")
                break

        print("\nSimulation completed.")

        run_dir = create_run_directory(scenario)
        save_vehicle_metrics(vehicle_metrics, run_dir)

    finally:
        update_vehicle_positions([])
        traci.close()


if __name__ == "__main__":
    main()