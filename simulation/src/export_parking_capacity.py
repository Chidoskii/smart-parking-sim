import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

xml_path = ROOT / "simulation/sumo/additionals/parking.add.xml"
config_path = ROOT / "shared/config/parking-lots.json"
output_path = ROOT / "shared/config/parking-capacity.json"

root = ET.parse(xml_path).getroot()
config = json.loads(config_path.read_text(encoding="utf-8"))

areas = {}

for area in root.findall(".//parkingArea"):
    area_id = area.get("id")
    roadside = int(area.get("roadsideCapacity", "0"))
    explicit = len(area.findall("space"))

    areas[area_id] = {
        "roadsideCapacity": roadside,
        "explicitSpaces": explicit,
        "capacity": roadside + explicit,
    }

lots = {}

for lot_id, lot in config["lots"].items():
    ids = lot["sumoParkingAreas"]

    missing = [area_id for area_id in ids if area_id not in areas]
    if missing:
        raise ValueError(f"{lot_id} has unknown areas: {missing}")

    lots[lot_id] = {
        "name": lot["name"],
        "parkingAreas": ids,
        "capacity": sum(areas[area_id]["capacity"] for area_id in ids),
    }

all_ids = [
    area_id
    for lot in lots.values()
    for area_id in lot["parkingAreas"]
]

if len(all_ids) != len(set(all_ids)):
    raise ValueError("Duplicate parking-area assignments detected")

if set(all_ids) != set(areas):
    raise ValueError("Parking-area mapping is incomplete")

output = {
    "totalCapacity": sum(area["capacity"] for area in areas.values()),
    "areas": areas,
    "lots": lots,
}

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(
    json.dumps(output, indent=2),
    encoding="utf-8",
)

print(f"Exported {len(areas)} parking areas")
print(f"Total capacity: {output['totalCapacity']}")

for lot_id, lot in lots.items():
    print(f"{lot_id}: {lot['capacity']} spaces")

print(f"Saved to {output_path}")