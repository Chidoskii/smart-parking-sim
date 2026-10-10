from pathlib import Path
import json
import traci

ROOT = Path(__file__).resolve().parents[2]

CONFIG = ROOT / "simulation/sumo/config/campus.sumocfg"
CAPACITY_FILE = ROOT / "shared/config/parking-capacity.json"


def main():
    with open(CAPACITY_FILE, "r", encoding="utf-8") as file:
        capacity_data = json.load(file)

    traci.start([
        "sumo",
        "-c",
        str(CONFIG),
        "--no-step-log",
        "true"
    ])

    try:
        sumo_areas = set(traci.parkingarea.getIDList())
        expected_areas = set(capacity_data["areas"])

        print(f"\nSUMO parking areas: {len(sumo_areas)}")
        print(f"Expected parking areas: {len(expected_areas)}")

        missing = expected_areas - sumo_areas
        extra = sumo_areas - expected_areas

        if missing or extra:
            print(f"Missing areas: {sorted(missing)}")
            print(f"Unexpected areas: {sorted(extra)}")
            raise RuntimeError("Parking area inventory mismatch")

        for step in range(300):
            traci.simulationStep()

            if step % 30 == 0:
                print(
                    f"\nSimulation time: "
                    f"{traci.simulation.getTime():.0f}s"
                )

                for lot_id, lot in capacity_data["lots"].items():
                    occupied = sum(
                        traci.parkingarea.getVehicleCount(area_id)
                        for area_id in lot["parkingAreas"]
                    )

                    capacity = lot["capacity"]

                    print(
                        f"{lot['name']}: "
                        f"{occupied} occupied / "
                        f"{capacity} inventory spaces"
                    )

    finally:
        traci.close()


if __name__ == "__main__":
    main()