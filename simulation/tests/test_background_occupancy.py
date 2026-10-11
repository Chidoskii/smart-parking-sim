
from pathlib import Path

import traci

ROOT = Path(__file__).resolve().parents[2]

SUMO_CONFIG = (
    ROOT / "simulation/sumo/config/background_parking.sumocfg"
)

PARKING_AREA = "hill_pa181138927#0"
EXPECTED_OCCUPANCY = 8
CAPACITY = 10


def main():
    print("Starting background parking test...")

    traci.start([
        "sumo",
        "-c",
        str(SUMO_CONFIG),
        "--end",
        "60",
    ])

    try:
        for step in range(60):
            traci.simulationStep()

            if step in [0, 1, 4, 9, 29, 59]:
                occupied = traci.parkingarea.getVehicleCount(
                    PARKING_AREA
                )

                vehicle_ids = traci.parkingarea.getVehicleIDs(
                    PARKING_AREA
                )

                print(
                    f"Time {traci.simulation.getTime():.0f}s | "
                    f"Occupied: {occupied}/{CAPACITY}"
                )

                print(f"  Parked vehicles: {list(vehicle_ids)}")

        final_occupancy = traci.parkingarea.getVehicleCount(
            PARKING_AREA
        )

        print("\n=== Test Result ===")

        if final_occupancy == EXPECTED_OCCUPANCY:
            print("PASS: All 8 background vehicles are parked.")
        else:
            print(
                f"FAIL: Expected {EXPECTED_OCCUPANCY} parked "
                f"vehicles, found {final_occupancy}."
            )

    finally:
        traci.close()


if __name__ == "__main__":
    main()
