import csv
import json
import time
import argparse
import xml.etree.ElementTree as ET

from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError

import traci

ROOT = Path(__file__).resolve().parents[2]

SUMO_CONFIG = (
    ROOT / "simulation/sumo/config/campus.sumocfg"
)

ROUTES_FILE = ROOT / "simulation/sumo/routes/test_parking.rou.xml"

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

SIMULATION_STEPS = 2400
OCCUPANCY_UPDATE_INTERVAL = 5
VEHICLE_UPDATE_INTERVAL = 1
GASOLINE_DENSITY_G_PER_L = 745.0
LITERS_PER_US_GALLON = 3.785411784
METERS_PER_MILE = 1609.344

# Delay between simulation steps so the dashboard
# can display occupancy changes.
STEP_DELAY = 0.1


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

def load_vehicle_assignments():
    root = ET.parse(ROUTES_FILE).getroot()
    assignments = {}

    for vehicle in root.findall("vehicle"):
        vehicle_id = vehicle.get("id")
        stop = vehicle.find("stop")

        if stop is not None:
            assignments[vehicle_id] = stop.get("parkingArea")

    return assignments

def save_vehicle_metrics(vehicle_metrics, run_dir):
    vehicle_results = run_dir / "vehicle_metrics.csv"

    fieldnames = [
        "vehicle_id",
        "assigned_parking_area",
        "departure_time",
        "parking_arrival_time",
        "time_to_parking",
        "waiting_time",
        "time_loss",
        "parking_success",
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

    args = parser.parse_args()

    scenario = args.scenario

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
        str(SUMO_CONFIG)
    ])

    try:
        parking_areas = traci.parkingarea.getIDList()

        assignments = load_vehicle_assignments()

        vehicle_metrics = {}

        for vehicle_id, area_id in assignments.items():
            vehicle_metrics[vehicle_id] = {
                "vehicle_id": vehicle_id,
                "assigned_parking_area": area_id,
                "departure_time": None,
                "parking_arrival_time": None,
                "time_to_parking": None,
                "waiting_time": None,
                "time_loss": None,
                "parking_success": False,
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
            # Record actual vehicle departures.
            for vehicle_id in traci.simulation.getDepartedIDList():
                if vehicle_id in vehicle_metrics:
                    vehicle_metrics[vehicle_id]["departure_time"] = current_time

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