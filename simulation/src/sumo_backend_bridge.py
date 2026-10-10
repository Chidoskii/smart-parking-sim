import json
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError

import traci

ROOT = Path(__file__).resolve().parents[2]

SUMO_CONFIG = (
    ROOT / "simulation/sumo/config/campus.sumocfg"
)

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

        print(f"Connected to {len(parking_areas)} parking areas")

        # Store the last occupancy successfully sent.
        last_occupancy = {}

        for step in range(SIMULATION_STEPS):
            traci.simulationStep()

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

    finally:
        traci.close()


if __name__ == "__main__":
    main()