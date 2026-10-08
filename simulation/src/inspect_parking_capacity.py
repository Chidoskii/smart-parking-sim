import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]

PARKING_XML = (
    ROOT
    / "simulation"
    / "sumo"
    / "additionals"
    / "parking.add.xml"
)

tree = ET.parse(PARKING_XML)
root = tree.getroot()

areas = []
total_capacity = 0

for area in root.findall(".//parkingArea"):
    area_id = area.get("id")

    roadside_capacity = int(
        area.get("roadsideCapacity", "0")
    )

    explicit_spaces = len(area.findall("space"))

    capacity = roadside_capacity + explicit_spaces

    areas.append({
        "id": area_id,
        "roadsideCapacity": roadside_capacity,
        "explicitSpaces": explicit_spaces,
        "capacity": capacity,
    })

    total_capacity += capacity

print(f"Total parking areas: {len(areas)}")
print(f"Total declared capacity: {total_capacity}")

print("\nParking area types:")

types = Counter()

for area in areas:
    roadside = area["roadsideCapacity"] > 0
    explicit = area["explicitSpaces"] > 0

    if roadside and explicit:
        types["Mixed"] += 1
    elif roadside:
        types["Roadside capacity only"] += 1
    elif explicit:
        types["Explicit spaces only"] += 1
    else:
        types["No declared capacity"] += 1

for name, count in types.items():
    print(f"{name}: {count}")

print("\nAreas requiring review:")

for area in areas:
    if (
        area["roadsideCapacity"] > 0
        and area["explicitSpaces"] > 0
    ) or area["capacity"] == 0:
        print(area)