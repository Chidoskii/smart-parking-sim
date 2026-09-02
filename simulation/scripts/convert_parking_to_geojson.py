import gzip
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import CRS, Transformer


ROOT = Path(__file__).resolve().parents[2]

NETWORK_FILE = ROOT / "simulation" / "sumo" / "network" / "osm.net.xml.gz"
PARKING_FILE = ROOT / "simulation" / "sumo" / "additionals" / "parking.add.xml"

OUTPUT_FILE = ROOT / "shared" / "geojson" / "parking-spaces.geojson"


def read_network_location():
    with gzip.open(NETWORK_FILE, "rt", encoding="utf-8") as file:
        tree = ET.parse(file)

    root = tree.getroot()
    location = root.find("location")

    if location is None:
        raise RuntimeError("No <location> element found in SUMO network.")

    net_offset = location.attrib["netOffset"]
    proj_parameter = location.attrib["projParameter"]

    offset_x, offset_y = map(float, net_offset.split(","))

    return offset_x, offset_y, proj_parameter


def create_transformer(proj_parameter):
    sumo_crs = CRS.from_proj4(proj_parameter)
    gps_crs = CRS.from_epsg(4326)

    return Transformer.from_crs(
        sumo_crs,
        gps_crs,
        always_xy=True,
    )


def sumo_to_lon_lat(x, y, offset_x, offset_y, transformer):
    projected_x = x - offset_x
    projected_y = y - offset_y

    longitude, latitude = transformer.transform(
        projected_x,
        projected_y,
    )

    return [longitude, latitude]


def create_parking_polygon(
    x,
    y,
    width,
    length,
    angle,
    offset_x,
    offset_y,
    transformer,
):
    """
    Create a rectangular GeoJSON polygon centered on a SUMO parking space.
    """

    half_width = width / 2
    half_length = length / 2

    # Rectangle centered at (0, 0)
    corners = [
        (-half_width, -half_length),
        (half_width, -half_length),
        (half_width, half_length),
        (-half_width, half_length),
    ]

    angle_radians = math.radians(angle)

    rotated_corners = []

    for corner_x, corner_y in corners:
        rotated_x = (
            corner_x * math.cos(angle_radians)
            - corner_y * math.sin(angle_radians)
        )

        rotated_y = (
            corner_x * math.sin(angle_radians)
            + corner_y * math.cos(angle_radians)
        )

        sumo_x = x + rotated_x
        sumo_y = y + rotated_y

        lon_lat = sumo_to_lon_lat(
            sumo_x,
            sumo_y,
            offset_x,
            offset_y,
            transformer,
        )

        rotated_corners.append(lon_lat)

    # GeoJSON polygons must close the ring
    rotated_corners.append(rotated_corners[0])

    return rotated_corners


def convert_parking_spaces():
    offset_x, offset_y, proj_parameter = read_network_location()

    transformer = create_transformer(proj_parameter)

    tree = ET.parse(PARKING_FILE)
    root = tree.getroot()

    features = []

    for parking_area in root.findall("parkingArea"):
        parking_area_id = parking_area.attrib["id"]

        for index, space in enumerate(parking_area.findall("space")):
            x = float(space.attrib["x"])
            y = float(space.attrib["y"])

            width = float(space.attrib.get("width", 2))
            length = float(space.attrib.get("length", 4))
            angle = float(space.attrib.get("angle", 0))

            polygon = create_parking_polygon(
                x,
                y,
                width,
                length,
                angle,
                offset_x,
                offset_y,
                transformer,
            )

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [polygon],
                },
                "properties": {
                    "id": f"{parking_area_id}_space_{index}",
                    "parkingAreaId": parking_area_id,
                    "status": "available",
                    "sumoX": x,
                    "sumoY": y,
                    "width": width,
                    "length": length,
                    "angle": angle,
                },
            }

            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(geojson, file, indent=2)

    print(f"Created {OUTPUT_FILE}")
    print(f"Converted {len(features)} parking spaces")


if __name__ == "__main__":
    convert_parking_spaces()