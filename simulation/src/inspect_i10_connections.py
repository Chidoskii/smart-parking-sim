from pathlib import Path
import sumolib

ROOT = Path(__file__).resolve().parents[2]

net = sumolib.net.readNet(
    str(ROOT / "simulation/sumo/network/osm.net.xml.gz")
)

entry_edge_id = "991195811"
entry_edge = net.getEdge(entry_edge_id)

print(f"\nI-10 entry edge: {entry_edge_id}")
print(f"Road: {entry_edge.getName()}")

print("\nOutgoing connections:")
for next_edge in entry_edge.getOutgoing().keys():
    print(
        f"  {next_edge.getID():30} "
        f"{next_edge.getName()}"
    )

print("\nIncoming connections:")
for previous_edge in entry_edge.getIncoming().keys():
    print(
        f"  {previous_edge.getID():30} "
        f"{previous_edge.getName()}"
    )

print("\nNearby freeway and ramp edges:")

x, y = entry_edge.getShape()[0]

nearby = net.getNeighboringEdges(x, y, r=1000)

for edge, distance in sorted(nearby, key=lambda item: item[1]):
    name = edge.getName().lower()
    edge_id = edge.getID().lower()

    if (
        "freeway" in name
        or "ramp" in edge_id
        or edge.getSpeed() >= 25
    ):
        print(
            f"  {edge.getID():35} "
            f"{edge.getName():30} "
            f"speed={edge.getSpeed():.1f} "
            f"distance={distance:.1f}m"
        )
