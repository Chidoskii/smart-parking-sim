import traci
import xml.etree.ElementTree as ET

PARKING_FILE = "simulation/sumo/additionals/parking.add.xml"

parking_root = ET.parse(PARKING_FILE).getroot()
capacities = {
    area.get("id"): int(area.get("roadsideCapacity"))
    for area in parking_root.findall("parkingArea")
}

SUMO_CONFIG = "simulation/sumo/config/campus.sumocfg"
ROUTES_FILE = "simulation/sumo/routes/combined_parking_test.rou.xml"

TARGET_VEHICLE = "parking_vehicle_14"
PREFERRED_AREA = "far_pa_56"

reassigned = False
selected_area = None

traci.start([
    "sumo",
    "-c", SUMO_CONFIG,
    "--route-files", ROUTES_FILE,
])

try:
    for step in range(1800):
        traci.simulationStep()
        current_time = traci.simulation.getTime()

        active = set(traci.vehicle.getIDList())

        if TARGET_VEHICLE in active and not reassigned:
            current_edge = traci.vehicle.getRoadID(TARGET_VEHICLE)

            # Test reassignment when approaching the original
            # parking area, before reaching the congested location.
            if current_time >= 900:
                parking_areas = []

                for area_id in traci.parkingarea.getIDList():
                    capacity = capacities.get(area_id, 0)
                    occupied = traci.parkingarea.getVehicleCount(area_id)

                    if area_id != PREFERRED_AREA and occupied < capacity:
                        parking_areas.append(area_id)

                print(
                    f"Time {current_time:.0f}s | "
                    f"Current edge: {current_edge} | "
                    f"Available alternatives: {len(parking_areas)}"
                )

                if parking_areas:
                    selected_area = parking_areas[0]
                    print(
                        f"Selected alternative: {selected_area} | "
                        f"Capacity: {capacities[selected_area]} | "
                        f"Occupied: {traci.parkingarea.getVehicleCount(selected_area)}"
                    )

                    try:
                        traci.vehicle.rerouteParkingArea(
                            TARGET_VEHICLE,
                            selected_area,
                        )

                        reassigned = True

                        print(
                            f"REASSIGNED {TARGET_VEHICLE}: "
                            f"{PREFERRED_AREA} -> {selected_area}"
                        )

                    except traci.TraCIException as error:
                        print("Reassignment failed:", error)
                        break

        if reassigned and step % 100 == 0:
            print(
                f"Time {current_time:.0f}s | "
                f"Vehicle active: {TARGET_VEHICLE in active}"
            )

        if reassigned and selected_area is not None:
            parked = traci.parkingarea.getVehicleIDs(selected_area)

            if TARGET_VEHICLE in parked:
                print(
                    f"\nSUCCESS: {TARGET_VEHICLE} "
                    f"parked at {selected_area} "
                    f"at time {current_time:.0f}s"
                )
                break

    if not reassigned:
        print("\nNo reassignment was performed.")

finally:
    traci.close()
