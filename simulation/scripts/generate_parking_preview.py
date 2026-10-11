
import argparse
import gzip
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import CRS, Transformer


ROOT = Path(__file__).resolve().parents[2]

NETWORK_FILE = ROOT / "simulation/sumo/network/osm.net.xml.gz"
PARKING_FILE = ROOT / "simulation/sumo/additionals/parking.add.xml"
LOTS_FILE = ROOT / "shared/config/parking-lots.json"
LAYOUT_FILE = ROOT / "shared/config/parking-layouts.json"
OUTPUT_FILE = ROOT / "shared/geojson/parking-spaces-preview.geojson"


def interpolate(shape, distance):
    lengths = [
        math.dist(a, b)
        for a, b in zip(shape, shape[1:])
    ]

    remaining = max(0, min(distance, sum(lengths)))

    for (ax, ay), (bx, by), length in zip(
        shape, shape[1:], lengths
    ):
        if length > 0 and remaining <= length:
            t = remaining / length

            return (
                ax + t * (bx - ax),
                ay + t * (by - ay),
            ), (
                (bx - ax) / length,
                (by - ay) / length,
            )

        remaining -= length

    ax, ay = shape[-2]
    bx, by = shape[-1]
    length = math.dist((ax, ay), (bx, by))

    if length == 0:
        raise ValueError("Lane ends with a zero-length segment")

    return (bx, by), (
        (bx - ax) / length,
        (by - ay) / length,
    )


def create_polygon(
    cx, cy, dx, dy,
    width, length,
    transformer, offset_x, offset_y
):
    normal_x, normal_y = -dy, dx

    corners = []

    for along, across in [
        (-width / 2, -length / 2),
        (width / 2, -length / 2),
        (width / 2, length / 2),
        (-width / 2, length / 2),
    ]:
        x = cx + along * dx + across * normal_x
        y = cy + along * dy + across * normal_y

        lon, lat = transformer.transform(
            x - offset_x,
            y - offset_y,
        )

        corners.append([lon, lat])

    corners.append(corners[0])

    return {
        "type": "Polygon",
        "coordinates": [corners],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lot",
        default="J",
        help="Campus lot to generate, e.g. J, M, PS1, F2",
    )
    parser.add_argument(
        "--mixed-only",
        action="store_true",
        help="Generate roadside spaces only for areas with explicit spaces",
    )
    args = parser.parse_args()

    lot_id = args.lot.upper()

    with open(LOTS_FILE, encoding="utf-8") as file:
        lots_config = json.load(file)["lots"]

    if lot_id != "ALL" and lot_id not in lots_config:
        raise ValueError(f"Unknown campus lot: {lot_id}")

    area_to_lot = {}

    for campus_lot, lot_config in lots_config.items():
        for area_id in lot_config["sumoParkingAreas"]:
            if area_id in area_to_lot:
                raise ValueError(
                    f"Duplicate parking-area assignment: {area_id}"
                )

            area_to_lot[area_id] = campus_lot

    target_areas = (
        set(area_to_lot)
        if lot_id == "ALL"
        else set(lots_config[lot_id]["sumoParkingAreas"])
    )

    with open(LAYOUT_FILE, encoding="utf-8") as file:
        layout_config = json.load(file)

    defaults = layout_config["defaults"]
    overrides = layout_config.get("areas", {})

    with gzip.open(
        NETWORK_FILE, "rt", encoding="utf-8"
    ) as file:
        network = ET.parse(file).getroot()

    location = network.find("location")

    offset_x, offset_y = map(
        float,
        location.get("netOffset").split(","),
    )

    transformer = Transformer.from_crs(
        CRS.from_user_input(
            location.get("projParameter")
        ),
        CRS.from_epsg(4326),
        always_xy=True,
    )

    lanes = {
        lane.get("id"): lane
        for lane in network.iter("lane")
        if lane.get("id") and lane.get("shape")
    }

    parking = ET.parse(PARKING_FILE).getroot()

    features = []
    generated_areas = 0
    warnings = []

    for area in parking.findall("parkingArea"):
        area_id = area.get("id")

        if area_id not in target_areas:
            continue

        explicit_count = len(area.findall("space"))
        capacity = int(area.get("roadsideCapacity", "0"))

        if args.mixed_only:
            # Only generate roadside capacity for areas
            # that also contain explicit parking spaces.
            if explicit_count == 0:
                continue
        else:
            # Normal preview generation skips explicit areas.
            if explicit_count:
                warnings.append(
                    f"{area_id}: has {explicit_count} explicit spaces; "
                    "roadside geometry handled separately"
                )
                continue

        if capacity <= 0:
            warnings.append(
                f"{area_id}: no roadside capacity"
            )
            continue

        lane_id = area.get("lane")
        lane = lanes.get(lane_id)

        if lane is None:
            warnings.append(
                f"{area_id}: missing lane {lane_id}"
            )
            continue

        lane_length = float(
            lane.get("length", "0")
        )

        if lane_length <= 0:
            warnings.append(
                f"{area_id}: invalid lane length"
            )
            continue

        shape = [
            tuple(map(float, point.split(",")))
            for point in lane.get("shape").split()
        ]

        if len(shape) < 2:
            warnings.append(
                f"{area_id}: invalid lane shape"
            )
            continue

        geometric_length = sum(
            math.dist(a, b)
            for a, b in zip(shape, shape[1:])
        )

        start = float(
            area.get("startPos", "0")
        )
        end = float(
            area.get("endPos", str(lane_length))
        )

        if start < 0:
            start += lane_length

        if end < 0:
            end += lane_length

        start = max(0, min(lane_length, start))
        end = max(0, min(lane_length, end))

        segment_length = end - start

        if segment_length <= 0:
            warnings.append(
                f"{area_id}: invalid parking interval"
            )
            continue

        # SUMO parking areas use lefthand to indicate
        # which side of the lane the parking is located on.
        sumo_left = area.get("lefthand", "false").lower() in (
            "1", "true", "yes"
        )

        sumo_side = "left" if sumo_left else "right"

        settings = {
            **defaults,
            "side": sumo_side,
            **overrides.get(area_id, {}),
        }

        width = float(settings["spaceWidth"])
        length = float(settings["spaceLength"])
        lane_offset = float(settings["laneOffset"])
        row_spacing = float(settings["rowSpacing"])
        target_spacing = float(settings["targetSpacing"])

        if min(width, length, target_spacing) <= 0:
            raise ValueError(
                f"{area_id}: invalid space dimensions"
            )

        if row_spacing < length:
            warnings.append(
                f"{area_id}: rowSpacing may cause "
                "rectangles to overlap"
            )

        side = settings.get("side", "left")

        if side not in ("left", "right", "both"):
            raise ValueError(
                f"{area_id}: side must be left, right, or both"
            )

        # Default: calculate how many stalls can fit
        # along a row at the target spacing.
        default_per_row = max(
            1,
            math.floor(segment_length / target_spacing),
        )

        spaces_per_row = int(
            settings.get(
                "spacesPerRow",
                default_per_row,
            )
        )

        if spaces_per_row <= 0:
            raise ValueError(
                f"{area_id}: invalid spacesPerRow"
            )

        minimum_rows = math.ceil(
            capacity / spaces_per_row
        )

        rows = int(
            settings.get("rows", minimum_rows)
        )

        if rows < minimum_rows:
            raise ValueError(
                f"{area_id}: {rows} rows cannot hold "
                f"{capacity} spaces at "
                f"{spaces_per_row} per row"
            )

        actual_spacing = (
            segment_length / spaces_per_row
        )

        if actual_spacing < width:
            warnings.append(
                f"{area_id}: longitudinal rectangles "
                "may overlap"
            )

        for index in range(capacity):
            row = index // spaces_per_row
            column = index % spaces_per_row

            position = start + (
                (column + 0.5) / spaces_per_row
            ) * segment_length

            distance = (
                position * geometric_length / lane_length
            )

            (x, y), (dx, dy) = interpolate(
                shape, distance
            )

            if side == "both":
                # Alternate rows between the two sides of the lane.
                side_multiplier = 1 if row % 2 == 0 else -1
                row_depth = row // 2
            else:
                side_multiplier = 1 if side == "left" else -1
                row_depth = row

            lateral_offset = (
                lane_offset + row_depth * row_spacing
            )

            cx = x - dy * lateral_offset * side_multiplier
            cy = y + dx * lateral_offset * side_multiplier

            features.append({
                "type": "Feature",
                "properties": {
                    "id": (
                        f"{area_id}_roadside_{index}"
                        if args.mixed_only
                        else f"{area_id}_space_{index}"
                    ),
                    "parkingAreaId": area_id,
                    "campusLot": area_to_lot[area_id],
                    "status": "available",
                    "geometryType": "provisional",
                    "row": row,
                    "column": column,
                    "sumoX": round(cx, 3),
                    "sumoY": round(cy, 3),
                },
                "geometry": create_polygon(
                    cx, cy, dx, dy,
                    width, length,
                    transformer,
                    offset_x, offset_y,
                ),
            })

        generated_areas += 1

    output = {
        "type": "FeatureCollection",
        "features": features,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    output_file = (
        ROOT / "shared/geojson/parking-spaces-mixed.geojson"
        if args.mixed_only
        else OUTPUT_FILE
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_file.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print(f"Campus lot: {lot_id}")
    print(f"Parking areas generated: {generated_areas}")
    print(f"Parking rectangles generated: {len(features)}")
    print(f"Preview saved: {output_file}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()
