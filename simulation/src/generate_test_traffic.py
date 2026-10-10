from pathlib import Path
import xml.etree.ElementTree as ET

import sumolib

ROOT = Path(__file__).resolve().parents[2]

NETWORK = ROOT / "simulation/sumo/network/osm.net.xml.gz"
PARKING = ROOT / "simulation/sumo/additionals/parking.add.xml"

OUTPUT = ROOT / "simulation/sumo/routes/test_parking.rou.xml"

ENTRY_EDGE = "180618650#0"
PARKING_AREA = "hill_pa_100"

VEHICLE_COUNT = 10
DEPARTURE_INTERVAL = 20
PARKING_DURATION = 300


def main():
    net = sumolib.net.readNet(str(NETWORK))

    parking_root = ET.parse(PARKING).getroot()

    parking_area = next(
        (
            area for area in parking_root.findall(".//parkingArea")
            if area.get("id") == PARKING_AREA
        ),
        None
    )

    if parking_area is None:
        raise ValueError(f"Unknown parking area: {PARKING_AREA}")

    parking_lane = net.getLane(parking_area.get("lane"))
    destination_edge = parking_lane.getEdge()

    entry_edge = net.getEdge(ENTRY_EDGE)

    route, cost = net.getShortestPath(
        entry_edge,
        destination_edge,
        vClass="passenger"
    )

    if not route:
        raise RuntimeError(
            f"No route from {ENTRY_EDGE} to {PARKING_AREA}"
        )

    route_edges = " ".join(edge.getID() for edge in route)

    routes_root = ET.Element("routes")

    ET.SubElement(
        routes_root,
        "vType",
        {
            "id": "passenger_car",
            "vClass": "passenger",
            "accel": "2.6",
            "decel": "4.5",
            "length": "5",
            "minGap": "2.5",
            "maxSpeed": "13.9"
        }
    )

    ET.SubElement(
        routes_root,
        "route",
        {
            "id": "route_to_parking",
            "edges": route_edges
        }
    )

    for i in range(VEHICLE_COUNT):
        vehicle = ET.SubElement(
            routes_root,
            "vehicle",
            {
                "id": f"parking_vehicle_{i}",
                "type": "passenger_car",
                "route": "route_to_parking",
                "depart": str(i * DEPARTURE_INTERVAL)
            }
        )

        ET.SubElement(
            vehicle,
            "stop",
            {
                "parkingArea": PARKING_AREA,
                "duration": str(PARKING_DURATION)
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.ElementTree(routes_root)
    ET.indent(tree, space="    ")

    tree.write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"Generated {VEHICLE_COUNT} vehicles")
    print(f"Entry edge: {ENTRY_EDGE}")
    print(f"Parking area: {PARKING_AREA}")
    print(f"Route edges: {len(route)}")
    print(f"Route cost: {cost:.1f}")
    print(f"Saved to: {OUTPUT}")


if __name__ == "__main__":
    main()