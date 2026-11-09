
from pathlib import Path
import xml.etree.ElementTree as ET
import sumolib

ROOT = Path(__file__).resolve().parents[2]

net = sumolib.net.readNet(
    str(ROOT / "simulation/sumo/network/osm.net.xml.gz")
)

parking_root = ET.parse(
    ROOT / "simulation/sumo/additionals/parking.add.xml"
).getroot()

parking_edges = {
    area.get("id"): area.get("lane").rsplit("_", 1)[0]
    for area in parking_root.iter("parkingArea")
}

return_exits = {
    "Kellogg Drive": "180618649#1",
    "West Temple Avenue": "1001728056",
    "I-10 direction": "-1203960827#1",
}

test_areas = [
    "far_pa_56",
    "far_pa_40",
    "hill_pa_105",
]

for parking_id in test_areas:
    start_edge = net.getEdge(parking_edges[parking_id])

    print(f"\nParking area: {parking_id}")

    for corridor, exit_id in return_exits.items():
        exit_edge = net.getEdge(exit_id)

        route, distance = net.getShortestPath(
            start_edge,
            exit_edge,
            vClass="passenger"
        )

        if route:
            print(
                f"  {corridor}: REACHABLE "
                f"({distance:.1f} m, {len(route)} edges)"
            )
        else:
            print(f"  {corridor}: NO ROUTE")
