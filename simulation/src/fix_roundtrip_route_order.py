from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]

route_file = (
    ROOT / "simulation/sumo/routes/combined_parking_roundtrip.rou.xml"
)

tree = ET.parse(route_file)
root = tree.getroot()

# Place vehicle types and route definitions before vehicles.
priority = {
    "vType": 0,
    "route": 1,
    "routeDistribution": 1,
    "vehicle": 2,
    "flow": 2,
    "trip": 2,
}

children = list(root)

children.sort(
    key=lambda element: priority.get(element.tag, 3)
)

root[:] = children

ET.indent(tree, space="    ")

tree.write(
    route_file,
    encoding="utf-8",
    xml_declaration=True
)

print("Route definitions moved before vehicles.")
print(f"Updated: {route_file}")
