import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_FILE = (
    PROJECT_ROOT
    / "simulation/sumo/routes/test_parking.rou.xml"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "simulation/sumo/routes/combined_parking_test.rou.xml"
)

TARGET_PARKING_AREA = "far_pa_56"
BACKGROUND_ROUTE_ID = "route_3"


def generate_combined_routes(
    background_count=29,
    warmup=600,
    background_duration=3600,
):
    if not 0 <= background_count <= 30:
        raise ValueError("Background count must be between 0 and 30.")

    if warmup < 0 or background_duration <= 0:
        raise ValueError("Warm-up must be nonnegative and duration positive.")

    source_root = ET.parse(SOURCE_FILE).getroot()
    combined_root = ET.Element("routes")

    original_vehicles = source_root.findall("vehicle")

    # Copy original vehicle types and route definitions.
    for element in source_root:
        if element.tag not in {"vehicle", "flow", "trip", "person"}:
            combined_root.append(copy.deepcopy(element))

    # Reuse route_3 for background vehicles.
    background_route = next(
        (
            route
            for route in source_root.findall("route")
            if route.get("id") == BACKGROUND_ROUTE_ID
        ),
        None,
    )

    if background_route is None:
        raise ValueError(f"Route {BACKGROUND_ROUTE_ID} not found.")

    route_copy = copy.deepcopy(background_route)
    route_copy.set("id", "background_route")
    combined_root.append(route_copy)

    # Background vehicles depart first.
    for i in range(background_count):
        vehicle = ET.SubElement(
            combined_root,
            "vehicle",
            {
                "id": f"background_vehicle_{i}",
                "type": "passenger_car",
                "route": "background_route",
                "depart": str(i),
            },
        )

        ET.SubElement(
            vehicle,
            "stop",
            {
                "parkingArea": TARGET_PARKING_AREA,
                "duration": str(background_duration),
            },
        )

    # Preserve the experimental routes and parking assignments,
    # but shift departures by the warm-up duration.
    shifted_vehicles = []

    for original_vehicle in original_vehicles:
        vehicle = copy.deepcopy(original_vehicle)

        departure = float(vehicle.get("depart"))
        vehicle.set("depart", f"{departure + warmup:g}")

        shifted_vehicles.append(vehicle)

    # SUMO expects vehicles in departure-time order.
    all_vehicles = list(combined_root.findall("vehicle"))
    all_vehicles.extend(shifted_vehicles)

    for vehicle in combined_root.findall("vehicle"):
        combined_root.remove(vehicle)

    all_vehicles.sort(key=lambda v: float(v.get("depart")))

    for vehicle in all_vehicles:
        combined_root.append(vehicle)

    tree = ET.ElementTree(combined_root)
    ET.indent(tree, space="    ")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"Created: {OUTPUT_FILE}")
    print(f"Background vehicles: {background_count}")
    print(f"Experimental vehicles: {len(original_vehicles)}")
    print(f"Warm-up: {warmup} seconds")
    print(f"Background parking duration: {background_duration} seconds")
    print(f"Total vehicles: {len(all_vehicles)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--background-count", type=int, default=29)
    parser.add_argument("--warmup", type=int, default=600)
    parser.add_argument("--background-duration", type=int, default=3600)

    args = parser.parse_args()

    generate_combined_routes(
        background_count=args.background_count,
        warmup=args.warmup,
        background_duration=args.background_duration,
    )
