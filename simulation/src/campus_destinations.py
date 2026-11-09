# Campus destinations using SUMO network coordinates.
# Coordinates represent approximate building entrances.

CAMPUS_DESTINATIONS = {
    "college_of_science": {
        "name": "College of Science",
        "x": 886.24,
        "y": 900.80,
    },
}

DEFAULT_DESTINATION = "college_of_science"


def get_destination_coordinates(destination_id=DEFAULT_DESTINATION):
    destination = CAMPUS_DESTINATIONS[destination_id]

    return (
        destination["x"],
        destination["y"],
    )