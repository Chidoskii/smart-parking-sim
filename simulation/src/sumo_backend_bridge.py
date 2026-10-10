import csv
import json
import time
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
VEHICLE_RESULTS = RESULTS_DIR / "vehicle_metrics.csv"

BACKEND_URL = "http://localhost:5000"

SIMULATION_STEPS = 2400
UPDATE_INTERVAL = 5

# Delay between simulation steps so the dashboard
# can display occupancy changes.
STEP_DELAY = 0.05


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


def load_vehicle_assignments():
    root = ET.parse(ROUTES_FILE).getroot()
    assignments = {}

    for vehicle in root.findall("vehicle"):
        vehicle_id = vehicle.get("id")
        stop = vehicle.find("stop")

        if stop is not None:
            assignments[vehicle_id] = stop.get("parkingArea")

    return assignments

def save_vehicle_metrics(vehicle_metrics):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "vehicle_id",
        "assigned_parking_area",
        "departure_time",
        "parking_arrival_time",
        "time_to_parking",
        "waiting_time",
        "time_loss",
        "parking_success",
    ]

    with open(
        VEHICLE_RESULTS,
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

    print(f"\nVehicle metrics saved to: {VEHICLE_RESULTS}")
    print(f"Successfully parked: {successful}/{len(vehicle_metrics)}")


def main():
    print("Starting SUMO-to-backend bridge...")

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
            }

        print(f"Connected to {len(parking_areas)} parking areas")

        # Store the last occupancy successfully sent.
        last_occupancy = {}

        for step in range(SIMULATION_STEPS):
            traci.simulationStep()
            current_time = traci.simulation.getTime()

            # Record actual vehicle departures.
            for vehicle_id in traci.simulation.getDepartedIDList():
                if vehicle_id in vehicle_metrics:
                    vehicle_metrics[vehicle_id]["departure_time"] = current_time

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

            if step % UPDATE_INTERVAL == 0:
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

            time.sleep(STEP_DELAY)
            if traci.simulation.getMinExpectedNumber() == 0:
                print("\nAll vehicles have completed their routes.")
                break

        print("\nSimulation completed.")
        save_vehicle_metrics(vehicle_metrics)

    finally:
        traci.close()


if __name__ == "__main__":
    main()