from pathlib import Path
import xml.etree.ElementTree as ET

import sumolib

ROOT = Path(__file__).resolve().parents[2]

NETWORK = ROOT / "simulation/sumo/network/osm.net.xml.gz"
PARKING = ROOT / "simulation/sumo/additionals/parking.add.xml"

ENTRY_EDGE_IDS = [
    "156927285",
    "180618650#0",
    "405201550",
    "406206827#0",
    "406465877",
    "44219693",
    "991195811",
]


def main():
    net = sumolib.net.readNet(str(NETWORK))

    parking_root = ET.parse(PARKING).getroot()

    parking_areas = parking_root.findall(".//parkingArea")

    print("\n=== Parking Route Validation ===")

    for entry_id in ENTRY_EDGE_IDS:
        entry_edge = net.getEdge(entry_id)

        reachable = []

        for area in parking_areas:
            area_id = area.get("id")
            lane_id = area.get("lane")

            # Parking-area lane IDs end with the lane index.
            # Resolve the lane through SUMO rather than
            # manually manipulating the lane ID.
            try:
                lane = net.getLane(lane_id)
                destination_edge = lane.getEdge()
            except KeyError:
                continue

            if not destination_edge.allows("passenger"):
                continue

            route, cost = net.getShortestPath(
                entry_edge,
                destination_edge,
                vClass="passenger",
            )

            if route:
                reachable.append((area_id, cost))

        reachable.sort(key=lambda item: item[1])

        print(f"\nEntry edge: {entry_id}")
        print(f"Reachable parking areas: {len(reachable)}")

        for area_id, cost in reachable[:5]:
            print(
                f"  {area_id}: "
                f"route cost = {cost:.1f}"
            )


if __name__ == "__main__":
    main()