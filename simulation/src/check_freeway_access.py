from pathlib import Path
import sumolib

ROOT = Path(__file__).resolve().parents[2]

net = sumolib.net.readNet(
    str(ROOT / "simulation/sumo/network/osm.net.xml.gz")
)

freeway_edges = [
    edge for edge in net.getEdges()
    if "san bernardino freeway" in edge.getName().lower()
]

print(f"Total freeway edges: {len(freeway_edges)}")

for edge in freeway_edges:
    print(f"\nFreeway edge: {edge.getID()}")
    print(f"  From: {edge.getFromNode().getID()}")
    print(f"  To:   {edge.getToNode().getID()}")

    print("  Incoming connections:")

    incoming = edge.getIncoming()

    if not incoming:
        print("    NONE")

    for previous_edge in incoming:
        print(
            f"    {previous_edge.getID():35} "
            f"{previous_edge.getName()}"
        )

    print("  Outgoing connections:")

    outgoing = edge.getOutgoing()

    if not outgoing:
        print("    NONE")

    for next_edge in outgoing:
        print(
            f"    {next_edge.getID():35} "
            f"{next_edge.getName()}"
        )
