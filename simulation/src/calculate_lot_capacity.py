import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PARKING_XML = (
    ROOT / "simulation/sumo/additionals/parking.add.xml"
)

LOT_CONFIG = (
    ROOT / "shared/config/parking-lots.json"
)

tree = ET.parse(PARKING_XML)
parking_root = tree.getroot()

with open(LOT_CONFIG, "r", encoding="utf-8") as file:
    config = json.load(file)

# Calculate capacity for each SUMO parking area
area_capacities = {}

for area in parking_root.findall(".//parkingArea"):
    area_id = area.get("id")

    roadside = int(area.get("roadsideCapacity", "0"))
    explicit = len(area.findall("space"))

    area_capacities[area_id] = roadside + explicit

# Aggregate capacity by CPP lot
assigned_areas = set()
total_capacity = 0

for lot_id, lot in config["lots"].items():
    area_ids = lot["sumoParkingAreas"]

    capacity = sum(
        area_capacities.get(area_id, 0)
        for area_id in area_ids
    )

    missing = [
        area_id
        for area_id in area_ids
        if area_id not in area_capacities
    ]

    assigned_areas.update(area_ids)
    total_capacity += capacity

    print(f"\n{lot['name']} ({lot_id})")
    print(f"  Parking areas: {len(area_ids)}")
    print(f"  Declared capacity: {capacity}")

    if missing:
        print(f"  WARNING: Unknown area IDs: {missing}")

# Validate assignments
unassigned = set(area_capacities) - assigned_areas

print("\n--- Summary ---")
print(f"Total assigned capacity: {total_capacity}")
print(f"Total SUMO capacity: {sum(area_capacities.values())}")
print(f"Unassigned parking areas: {len(unassigned)}")

if unassigned:
    print("Unassigned IDs:", sorted(unassigned))