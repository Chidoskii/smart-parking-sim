from pathlib import Path
import xml.etree.ElementTree as ET
import sumolib

ROOT = Path(__file__).resolve().parents[2]

NETWORK_FILE = ROOT / "simulation/sumo/network/osm.net.xml.gz"
PARKING_FILE = ROOT / "simulation/sumo/additionals/parking.add.xml"

INPUT_ROUTES = (
    ROOT / "simulation/sumo/routes/combined_parking_test.rou.xml"
)

OUTPUT_ROUTES = (
    ROOT / "simulation/sumo/routes/combined_parking_roundtrip.rou.xml"
)

ENTRY_TO_EXIT = {
    "180618650#0": "180618649#1",
    "405201550": "1001728056",
    "991195811": "-1203960827#1",
}

net = sumolib.net.readNet(str(NETWORK_FILE))

parking_root = ET.parse(PARKING_FILE).getroot()

parking_edges = {
    area.get("id"): area.get("lane").rsplit("_", 1)[0]
    for area in parking_root.iter("parkingArea")
}

tree = ET.parse(INPUT_ROUTES)
root = tree.getroot()

routes = {
    route.get("id"): route
    for route in root.findall("route")
}

generated = 0

for vehicle in root.findall("vehicle"):
    vehicle_id = vehicle.get("id", "")

    # Leave background vehicles unchanged.
    if not vehicle_id.startswith("parking_vehicle_"):
        continue

    route_id = vehicle.get("route")
    original_route = routes[route_id]
    original_edges = original_route.get("edges").split()

    entry_edge_id = original_edges[0]
    exit_edge_id = ENTRY_TO_EXIT.get(entry_edge_id)

    if exit_edge_id is None:
        raise ValueError(
            f"No return exit configured for {entry_edge_id}"
        )

    stop = vehicle.find("stop")
    parking_id = stop.get("parkingArea")
    parking_edge_id = parking_edges[parking_id]

    return_route, distance = net.getShortestPath(
        net.getEdge(parking_edge_id),
        net.getEdge(exit_edge_id),
        vClass="passenger"
    )

    if not return_route:
        raise ValueError(
            f"No return route from {parking_id} "
            f"to {exit_edge_id}"
        )

    return_edge_ids = [
        edge.getID() for edge in return_route
    ]

    # Remove the duplicate parking edge at the join.
    combined_edges = (
        original_edges + return_edge_ids[1:]
    )

    # Create a vehicle-specific route so vehicles sharing
    # an original route can have independent return trips.
    new_route_id = f"roundtrip_{vehicle_id}"

    ET.SubElement(
        root,
        "route",
        id=new_route_id,
        edges=" ".join(combined_edges)
    )

    vehicle.set("route", new_route_id)

    generated += 1

tree.write(
    OUTPUT_ROUTES,
    encoding="utf-8",
    xml_declaration=True
)

print(f"Generated {generated} round-trip routes.")
print(f"Saved to: {OUTPUT_ROUTES}")
