from pathlib import Path
import json
import traci

ROOT = Path(__file__).resolve().parents[2]

CONFIG = ROOT / "simulation/sumo/config/campus.sumocfg"
CAPACITY_FILE = ROOT / "shared/config/parking-capacity.json"


def main():
    with open(CAPACITY_FILE, "r", encoding="utf-8") as file:
        inventory = json.load(file)

    traci.start([
        "sumo",
        "-c",
        str(CONFIG),
        "--no-step-log",
        "true"
    ])

    try:
        parking_areas = sorted(traci.parkingarea.getIDList())

        total_inventory = 0
        total_sumo = 0
        mismatches = []

        print("\n=== Parking Capacity Comparison ===")

        for area_id in parking_areas:
            inventory_capacity = inventory["areas"][area_id]["capacity"]

            sumo_capacity = int(
                traci.simulation.getParameter(
                    area_id,
                    "parkingArea.capacity"
                )
            )

            total_inventory += inventory_capacity
            total_sumo += sumo_capacity

            if inventory_capacity != sumo_capacity:
                mismatches.append({
                    "area": area_id,
                    "inventory": inventory_capacity,
                    "sumo": sumo_capacity
                })

        print(f"\nParking areas checked: {len(parking_areas)}")
        print(f"Inventory capacity: {total_inventory}")
        print(f"SUMO capacity: {total_sumo}")
        print(f"Capacity difference: {total_sumo - total_inventory}")

        print(f"\nMismatched areas: {len(mismatches)}")

        for mismatch in mismatches:
            print(
                f"{mismatch['area']}: "
                f"inventory={mismatch['inventory']}, "
                f"SUMO={mismatch['sumo']}"
            )

    finally:
        traci.close()


if __name__ == "__main__":
    main()
    