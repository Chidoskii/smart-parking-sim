from pathlib import Path
import xml.etree.ElementTree as ET

import sumolib

ROOT = Path(__file__).resolve().parents[2]

NETWORK = ROOT / "simulation/sumo/network/osm.net.xml.gz"
PARKING = ROOT / "simulation/sumo/additionals/parking.add.xml"


def main():
    print("Loading SUMO network...")

    net = sumolib.net.readNet(str(NETWORK))

    edges = net.getEdges()
    junctions = net.getNodes()

    print("\n=== Network Summary ===")
    print(f"Total edges: {len(edges)}")
    print(f"Total junctions: {len(junctions)}")

    # Identify roads that passenger vehicles can use.
    passenger_edges = [
        edge for edge in edges
        if edge.allows("passenger")
    ]

    print(f"Passenger-accessible edges: {len(passenger_edges)}")

    # Find roads with no incoming passenger-accessible edges.
    # These are candidates for vehicle entry points.
    passenger_ids = {edge.getID() for edge in passenger_edges}

    entry_edges = []

    for edge in passenger_edges:
        incoming = edge.getIncoming()

        incoming_passenger = [
            e for e in incoming
            if e.getID() in passenger_ids
        ]

        if not incoming_passenger:
            entry_edges.append(edge)

    print(f"Candidate entry edges: {len(entry_edges)}")

    print("\n=== Candidate Vehicle Entry Edges ===")

    for edge in entry_edges[:20]:
        print(
            f"Edge: {edge.getID()}, "
            f"Length: {edge.getLength():.1f} m"
        )

    # Inspect parking-area definitions.
    parking_root = ET.parse(PARKING).getroot()

    parking_areas = parking_root.findall(".//parkingArea")

    print("\n=== Parking Area Summary ===")
    print(f"Total parking areas: {len(parking_areas)}")

    print("\nSample parking destinations:")

    for area in parking_areas[:15]:
        print(
            f"ID: {area.get('id')}, "
            f"Lane: {area.get('lane')}"
        )


if __name__ == "__main__":
    main()