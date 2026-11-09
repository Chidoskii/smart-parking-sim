from pathlib import Path
import xml.etree.ElementTree as ET
import sumolib

ROOT = Path(__file__).resolve().parents[2]

NETWORK_FILE = ROOT / "simulation/sumo/network/osm.net.xml.gz"
PARKING_FILE = ROOT / "simulation/sumo/additionals/parking.add.xml"

net = sumolib.net.readNet(str(NETWORK_FILE))

return_edges = {
    "kellogg": "180618649#1",
    "temple": "1001728056",
    "i10": "156927274",
}

parking_root = ET.parse(PARKING_FILE).getroot()

parking_areas = {}

for area in parking_root.iter("parkingArea"):
    lane_id = area.get("lane")
    if not lane_id:
        continue

    edge_id = lane_id.rsplit("_", 1)[0]
    parking_areas[area.get("id")] = edge_id

test_parking_areas = [
    "far_pa_56",
    "far_pa_40",
    "hill_pa_105",
]

for parking_id in test_parking_areas:
    parking_edge_id = parking_areas.get(parking_id)

    if parking_edge_id is None:
        print(f"\n{parking_id}: NOT FOUND")
        continue

    parking_edge = net.getEdge(parking_edge_id)

    print(f"\nParking area: {parking_id}")
    print(f"Parking edge: {parking_edge_id}")

    for corridor, return_edge_id in return_edges.items():
        return_edge = net.getEdge(return_edge_id)

        route, cost = net.getShortestPath(
            parking_edge,
            return_edge,
            vClass="passenger"
        )

        if route:
            print(
                f"  {corridor}: REACHABLE "
                f"({cost:.1f} m, {len(route)} edges)"
            )
        else:
            print(f"  {corridor}: NO ROUTE")
