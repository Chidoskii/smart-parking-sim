import csv
import json
import time
import math
import sumolib
import argparse
import xml.etree.ElementTree as ET

from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError
try:
    from .parking_policies import get_parking_policy
    from .campus_destinations import (
        DEFAULT_DESTINATION,
        get_destination_coordinates,
    )
except ImportError:
    from parking_policies import get_parking_policy
    from campus_destinations import (
        DEFAULT_DESTINATION,
        get_destination_coordinates,
    )

import traci

ROOT = Path(__file__).resolve().parents[2]

SUMO_CONFIG = (
    ROOT / "simulation/sumo/config/campus.sumocfg"
)

ROUTES_FILE = ROOT / "simulation/sumo/routes/test_parking.rou.xml"
NETWORK_FILE = ROOT / "simulation/sumo/network/osm.net.xml.gz"
PARKING_FILE = ROOT / "simulation/sumo/additionals/parking.add.xml"

PARKING_SEARCH_DISTANCE_M = 200.0
BASELINE_SEARCH_DISTANCE = 200.0
BASELINE_LOCAL_RADIUS = 250.0
BASELINE_MAX_ALTERNATIVES = 3
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

def load_search_boundaries(route_file, parking_file):
    """
    Calculate a fixed search-start boundary for every vehicle.

    The boundary is 200 meters of route distance before the
    entrance to the vehicle's originally preferred parking area.
    """

    net = sumolib.net.readNet(str(NETWORK_FILE))

    routes_root = ET.parse(route_file).getroot()
    parking_root = ET.parse(parking_file).getroot()

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

        # Find the first occurrence of the preferred parking edge.
        # This represents the inbound journey to the parking area,
        # rather than a possible revisit during the return trip.
        parking_index = next(
            (
                i for i, edge_id in enumerate(edges)
                if edge_id == parking_edge
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
        "destination_building",
        "destination_displacement_m",
        "estimated_walking_time_s",
        "walking_distance_m",
        "walking_time_s",
        "departure_time",
        "parking_arrival_time",
        "parking_departure_time",
        "actual_parking_duration_s",
        "return_travel_time_s",
        "return_distance_m",
        "completed_return_trip",
        "exit_arrival_time",
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
        writer.writerows(
            {name: metrics.get(name) for name in fieldnames}
            for metrics in vehicle_metrics.values()
        )

    successful = sum(
        1
        for metrics in vehicle_metrics.values()
        if metrics["parking_success"]
    )

    print(f"\nVehicle metrics saved to: {vehicle_results}")
    print(f"Successfully parked: {successful}/{len(vehicle_metrics)}")

def get_parking_area_inventory(parking_file):
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

def get_reachable_parking_candidates(
    vehicle_id,
    inventory,
    reservations,
    destination_xy=None,
):
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

        candidate = {
            "id": area_id,
            "capacity": area["capacity"],
            "distance": route.length,
        }

        if destination_xy is not None:
            candidate["walking_distance"] = calculate_walking_distance(
                area_id,
                destination_xy,
            )

        candidates.append(candidate)

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


def get_parking_area_coordinates(parking_area_id):
    lane_id = traci.parkingarea.getLaneID(parking_area_id)

    start_pos = traci.parkingarea.getStartPos(parking_area_id)
    end_pos = traci.parkingarea.getEndPos(parking_area_id)

    midpoint = (start_pos + end_pos) / 2

    # Extract the edge ID and lane index from the lane ID.
    edge_id, lane_index = lane_id.rsplit("_", 1)

    return traci.simulation.convert2D(
        edge_id,
        midpoint,
        laneIndex=int(lane_index),
    )


def calculate_destination_displacement(
    preferred_parking_area,
    assigned_parking_area,
):
    preferred_x, preferred_y = get_parking_area_coordinates(
        preferred_parking_area
    )

    assigned_x, assigned_y = get_parking_area_coordinates(
        assigned_parking_area
    )

    return math.hypot(
        assigned_x - preferred_x,
        assigned_y - preferred_y,
    )


def estimate_walking_time(displacement_m, walking_speed_mps=1.4):
    return displacement_m / walking_speed_mps

def calculate_walking_distance(parking_area_id, destination_xy):
    parking_xy = get_parking_area_coordinates(parking_area_id)

    return math.dist(parking_xy, destination_xy)

def diagnose_parking_queues(vehicle_metrics, parking_file):
    inventory = {
        area["id"]: area
        for area in get_parking_area_inventory(parking_file)
    }

    print("\n--- PARKING QUEUE DIAGNOSTICS ---")

    for vehicle_id in traci.vehicle.getIDList():
        if not vehicle_id.startswith("parking_vehicle_"):
            continue

        metrics = vehicle_metrics.get(vehicle_id)

        if metrics is None or metrics["parking_success"]:
            continue

        area_id = metrics["assigned_parking_area"]
        area = inventory.get(area_id)

        if area is None:
            continue

        speed = traci.vehicle.getSpeed(vehicle_id)
        waiting_time = traci.vehicle.getWaitingTime(vehicle_id)

        if speed > 0.5 and waiting_time < 30:
            continue

        print(
            f"{vehicle_id} | "
            f"area={area_id} | "
            f"capacity={area['capacity']} | "
            f"occupied={area['occupied']} | "
            f"available={area['available']} | "
            f"speed={speed:.2f} | "
            f"waiting={waiting_time:.0f}s | "
            f"road={traci.vehicle.getRoadID(vehicle_id)}"
        )

def diagnose_vehicle_blocking(vehicle_id):
    if vehicle_id not in traci.vehicle.getIDList():
        return

    leader = traci.vehicle.getLeader(vehicle_id, 100)

    print(f"\n--- BLOCKING DIAGNOSTIC: {vehicle_id} ---")
    print("Road:", traci.vehicle.getRoadID(vehicle_id))
    print("Lane:", traci.vehicle.getLaneID(vehicle_id))
    print("Speed:", traci.vehicle.getSpeed(vehicle_id))
    print("Waiting:", traci.vehicle.getWaitingTime(vehicle_id))
    print("Leader:", leader)
    print("Current stop state:", traci.vehicle.getStopState(vehicle_id))

def handle_baseline_local_search(
    vehicle_metrics,
    parking_file,
    attempted_vehicles,
):
    inventory = {
        area["id"]: area
        for area in get_parking_area_inventory(parking_file)
    }

    for vehicle_id in traci.vehicle.getIDList():

        if vehicle_id not in vehicle_metrics:
            continue

        if vehicle_id in attempted_vehicles:
            continue

        metrics = vehicle_metrics[vehicle_id]

        if metrics["parking_success"]:
            continue

        preferred_area = metrics["assigned_parking_area"]
        preferred_info = inventory.get(preferred_area)

        if preferred_info is None:
            continue

        if preferred_info["available"] > 0:
            continue

        # Check whether the driver is approaching the preferred area.
        lane_id = traci.parkingarea.getLaneID(preferred_area)
        edge_id = traci.lane.getEdgeID(lane_id)
        lane_pos = traci.parkingarea.getStartPos(preferred_area)

        distance = traci.vehicle.getDrivingDistance(
            vehicle_id,
            edge_id,
            lane_pos,
        )

        if not 0 <= distance <= BASELINE_SEARCH_DISTANCE:
            continue

        # One local search attempt per vehicle for this first test.
        attempted_vehicles.add(vehicle_id)

        print(
            f"BASELINE SEARCH: {vehicle_id} "
            f"found {preferred_area} full "
            f"at distance {distance:.1f}m"
        )

        # Search only around the preferred parking area.
        preferred_xy = get_parking_area_coordinates(preferred_area)

        candidates = []

        for area in inventory.values():

            candidate_id = area["id"]

            if candidate_id == preferred_area:
                continue

            if area["available"] <= 0:
                continue

            candidate_xy = get_parking_area_coordinates(candidate_id)

            local_distance = math.dist(
                preferred_xy,
                candidate_xy,
            )

            if local_distance > BASELINE_LOCAL_RADIUS:
                continue

            candidates.append({
                "id": candidate_id,
                "local_distance": local_distance,
            })

        # Deterministic nearest-first local selection.
        candidates.sort(
            key=lambda area: (
                area["local_distance"],
                area["id"],
            )
        )

        if not candidates:
            print(
                f"BASELINE NO LOCAL PARKING: {vehicle_id}"
            )
            continue

        # Try at most three nearby alternatives.
        for candidate in candidates[:BASELINE_MAX_ALTERNATIVES]:

            candidate_id = candidate["id"]

            try:
                traci.vehicle.rerouteParkingArea(
                    vehicle_id,
                    candidate_id,
                )

            except traci.TraCIException as error:
                print(
                    f"BASELINE REROUTE FAILED: "
                    f"{vehicle_id} -> {candidate_id}: {error}"
                )
                continue

            metrics["assigned_parking_area"] = candidate_id
            metrics["parking_reassignments"] += 1

            print(
                f"BASELINE LOCAL REASSIGNMENT: "
                f"{vehicle_id} "
                f"{preferred_area} -> {candidate_id} "
                f"({candidate['local_distance']:.1f}m away)"
            )

            break

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

    parser.add_argument(
        "--parking-file",
        type=Path,
        default=PARKING_FILE,
        help="SUMO parking configuration file."
    )

    args = parser.parse_args()

    route_file = args.route_file.resolve()

    parking_file = args.parking_file.resolve()

    baseline_attempted_vehicles = set()

    if not parking_file.is_file():
        parser.error(f"Parking file not found: {parking_file}")

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
        "--additional-files",
        str(parking_file),
        "--time-to-teleport",
        "-1",
    ])

    try:
        parking_areas = traci.parkingarea.getIDList()
        parking_inventory = get_parking_area_inventory(parking_file)

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
        search_boundaries = load_search_boundaries(route_file, parking_file)

        print(f"Calculated search boundaries for {len(search_boundaries)} vehicles")

        vehicle_metrics = {}

        for vehicle_id, assignment in assignments.items():
            vehicle_metrics[vehicle_id] = {
                "vehicle_id": vehicle_id,
                "preferred_parking_area": assignment["preferred_parking_area"],
                "assigned_parking_area": assignment["assigned_parking_area"],
                "destination_building": DEFAULT_DESTINATION,
                "destination_displacement_m": None,
                "estimated_walking_time_s": None,
                "walking_distance_m": None,
                "walking_time_s": None,
                "departure_time": None,
                "parking_arrival_time": None,
                "parking_departure_time": None,
                "actual_parking_duration_s": None,
                "return_travel_time_s": None,
                "return_distance_m": None,
                "completed_return_trip": False,
                "exit_arrival_time": None,
                "_parking_departure_distance_m": None,
                "_last_distance_m": 0.0,
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

            if scenario == "baseline" and step % 10 == 0:
                handle_baseline_local_search(
                    vehicle_metrics,
                    parking_file,
                    baseline_attempted_vehicles,
                )

            # Diagnose parking queues and vehicle blocking.
            if step == 1200:
                diagnose_parking_queues(vehicle_metrics, parking_file)
                diagnose_vehicle_blocking("parking_vehicle_6")

            # Record vehicle teleportation.
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
                    
                    if scenario in ("availability", "smart"):
                        inventory = get_parking_area_inventory(parking_file)
                        reservations = get_pending_reservations(vehicle_metrics)

                        preferred_area = metrics["assigned_parking_area"]

                        # Exclude this vehicle's own reservation.
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
                            (
                                area for area in inventory
                                if area["id"] == preferred_area
                            ),
                            None,
                        )

                        if preferred_info is None:
                            print(
                                f"WARNING: Unknown parking area "
                                f"{preferred_area} for {vehicle_id}"
                            )
                            continue

                        preferred_full = (
                            occupancy[preferred_area]
                            >= preferred_info["capacity"]
                        )

                        # Availability acts only when preferred is full.
                        # Smart evaluates all feasible parking choices.
                        should_evaluate = (
                            scenario == "smart"
                            or (
                                scenario == "availability"
                                and preferred_full
                            )
                        )

                        if should_evaluate:
                            destination_xy = None

                            if scenario == "smart":
                                destination_xy = get_destination_coordinates(
                                    metrics["destination_building"]
                                )

                            candidates = get_reachable_parking_candidates(
                                vehicle_id,
                                inventory,
                                reservations,
                                destination_xy=destination_xy,
                            )

                            selected_area = policy.select_parking_area(
                                vehicle_id=vehicle_id,
                                destination=preferred_area,
                                parking_areas=candidates,
                                occupancy=occupancy,
                            )

                            if (
                                selected_area is not None
                                and selected_area != preferred_area
                            ):
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

                            elif selected_area is None:
                                print(
                                    f"NO AVAILABLE ALTERNATIVE: "
                                    f"{vehicle_id} at time {current_time:.0f}s"
                                )

            # Snapshot parked vehicles to detect departure after their stop.
            parked_now = set()
            for area_id in parking_areas:
                parked_now.update(traci.parkingarea.getVehicleIDs(area_id))

            # Detect experimental vehicles that have left their parking stop.
            for vehicle_id, metrics in vehicle_metrics.items():
                if (metrics["parking_arrival_time"] is None
                        or metrics["parking_departure_time"] is not None):
                    continue
                if vehicle_id in active_vehicle_ids and vehicle_id not in parked_now:
                    metrics["parking_departure_time"] = current_time
                    metrics["actual_parking_duration_s"] = round(
                        current_time - metrics["parking_arrival_time"], 2
                    )
                    metrics["_parking_departure_distance_m"] = traci.vehicle.getDistance(vehicle_id)
                    print(f"LEFT PARKING: {vehicle_id} at {current_time:.0f}s")

            # Detect completed trips. SUMO reports arrived IDs when a route ends.
            for vehicle_id in traci.simulation.getArrivedIDList():
                if vehicle_id not in vehicle_metrics:
                    continue
                metrics = vehicle_metrics[vehicle_id]
                if metrics["parking_departure_time"] is not None:
                    metrics["exit_arrival_time"] = current_time
                    metrics["return_travel_time_s"] = round(
                        current_time - metrics["parking_departure_time"], 2
                    )
                    start_distance = metrics["_parking_departure_distance_m"]
                    if start_distance is not None:
                        metrics["return_distance_m"] = round(
                            max(0.0, metrics["_last_distance_m"] - start_distance), 2
                        )
                    metrics["completed_return_trip"] = not metrics["teleported"]

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
                metrics["_last_distance_m"] = metrics["distance_m"]
                metrics["distance_miles"] = (metrics["distance_m"] / METERS_PER_MILE)

            # Preserve the last observed odometer reading after parking too.
            # This does not change the original inbound-only distance metric.
            for vehicle_id, metrics in vehicle_metrics.items():
                if vehicle_id in active_vehicle_ids:
                    metrics["_last_distance_m"] = traci.vehicle.getDistance(vehicle_id)

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

                        # Calculate walking distance from the assigned parking area
                        # to the vehicle's desired campus building.
                        destination_id = metrics["destination_building"]

                        destination_xy = get_destination_coordinates(destination_id)

                        walking_distance = calculate_walking_distance(
                            area_id,
                            destination_xy,
                        )

                        metrics["walking_distance_m"] = round(walking_distance, 2)

                        metrics["walking_time_s"] = round(
                            estimate_walking_time(walking_distance), 2
                        )

                        # Measure displacement from the originally preferred parking area
                        # to the parking area where the vehicle actually parked.
                        preferred_area = metrics["preferred_parking_area"]
                        final_area = metrics["assigned_parking_area"]

                        if preferred_area and final_area:
                            displacement = calculate_destination_displacement(
                                preferred_area,
                                final_area,
                            )

                            metrics["destination_displacement_m"] = round(
                                displacement, 2
                            )

                            metrics["estimated_walking_time_s"] = round(
                                estimate_walking_time(displacement), 2
                            )

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