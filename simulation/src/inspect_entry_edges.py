from pathlib import Path
import sumolib

ROOT = Path(__file__).resolve().parents[2]
NETWORK_FILE = ROOT / "simulation/sumo/network/osm.net.xml.gz"

net = sumolib.net.readNet(str(NETWORK_FILE))

entry_edges = [
    "180618650#0",
    "405201550",
    "991195811",
]

for edge_id in entry_edges:
    edge = net.getEdge(edge_id)

    print(f"Road name: {edge.getName()}")
    print(f"From node: {edge.getFromNode().getID()}")
    print(f"To node: {edge.getToNode().getID()}")
    shape = edge.getShape()

    x, y = shape[0]
    lon, lat = net.convertXY2LonLat(x, y)

    print(f"\nEdge: {edge_id}")
    print(f"Length: {edge.getLength():.1f} m")
    print(f"Speed: {edge.getSpeed():.1f} m/s")
    print(f"SUMO coordinates: ({x:.2f}, {y:.2f})")
    print(f"GPS coordinates: ({lat:.6f}, {lon:.6f})")

    print("\nNearby candidate return edges:")

    x, y = edge.getShape()[0]

    nearby_edges = net.getNeighboringEdges(x, y, r=150)

    for candidate, distance in sorted(
        nearby_edges,
        key=lambda item: item[1]
    ):
        if candidate.getID() == edge_id:
            continue

        print(
            f"  {candidate.getID():25} "
            f"{candidate.getName():30} "
            f"distance={distance:.1f}m"
        )
