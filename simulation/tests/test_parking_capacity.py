from pathlib import Path
import json
import traci

# Project paths
ROOT = Path(__file__).resolve().parents[2]

CONFIG = ROOT / "simulation/sumo/config/campus.sumocfg"
CAPACITY_FILE = ROOT / "shared/config/parking-capacity.json"


def test_parameter(domain_name, getter, area_id, parameter):
    """Attempt to retrieve a parking-area parameter."""

    try:
        value = getter(area_id, parameter)

        if value == "":
            return "Empty response (parameter may be unsupported)"

        return repr(value)

    except traci.TraCIException as error:
        return f"Unsupported: {error}"


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
        parking_areas = traci.parkingarea.getIDList()

        print("\n=== SUMO Parking Capacity Test ===")
        print(f"Total parking areas: {len(parking_areas)}")

        # Test a few representative parking areas
        test_areas = [
            "hill_pa_100",
            "far_pa_14",
            "far_pa_2",
            "far_pa_44"
        ]

        for area_id in test_areas:

            if area_id not in parking_areas:
                print(f"\nSkipping unknown area: {area_id}")
                continue

            print(f"\n--- {area_id} ---")

            inventory_capacity = (
                capacity_data["areas"][area_id]["capacity"]
            )

            print(f"Inventory capacity: {inventory_capacity}")

            print(
                "TraCI vehicle count:",
                traci.parkingarea.getVehicleCount(area_id)
            )

            for parameter in [
                "parkingArea.capacity",
                "parkingArea.occupancy"
            ]:

                parking_result = test_parameter(
                    "parkingarea",
                    traci.parkingarea.getParameter,
                    area_id,
                    parameter
                )

                simulation_result = test_parameter(
                    "simulation",
                    traci.simulation.getParameter,
                    area_id,
                    parameter
                )

                print(f"\nParameter: {parameter}")
                print(f"  parkingarea domain: {parking_result}")
                print(f"  simulation domain:  {simulation_result}")

    finally:
        traci.close()


if __name__ == "__main__":
    main()
    