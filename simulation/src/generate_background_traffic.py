
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCE_FILE = ROOT / "simulation/sumo/routes/test_parking.rou.xml"
OUTPUT_FILE = ROOT / "simulation/sumo/routes/parking_scarcity_test.rou.xml"


def generate_background_traffic(count=29):
    root = ET.parse(SOURCE_FILE).getroot()
    test_root = ET.Element("routes")

    # Copy vehicle type.
    vehicle_type = root.find("vType")
    test_root.append(
        ET.fromstring(ET.tostring(vehicle_type))
    )

    # Copy route used by parking_vehicle_3.
    original_route = next(
        route for route in root.findall("route")
        if route.get("id") == "route_3"
    )

    route_copy = ET.fromstring(ET.tostring(original_route))
    route_copy.set("id", "background_route")
    test_root.append(route_copy)

    # Generate background vehicles.
    for i in range(count):
        vehicle = ET.SubElement(
            test_root,
            "vehicle",
            {
                "id": f"background_vehicle_{i}",
                "type": "passenger_car",
                "route": "background_route",
                "depart": str(i),
            }
        )

        ET.SubElement(
            vehicle,
            "stop",
            {
                "parkingArea": "far_pa_56",
                "duration": "1200",
            }
        )

    tree = ET.ElementTree(test_root)
    ET.indent(tree, space="    ")

    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"Created: {OUTPUT_FILE}")
    print(f"Background vehicles: {count}")
    print("Parking area: far_pa_56")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--count",
        type=int,
        default=29
    )

    args = parser.parse_args()

    generate_background_traffic(args.count)
