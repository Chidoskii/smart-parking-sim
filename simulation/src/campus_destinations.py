
# Campus destinations using SUMO network coordinates.
# Coordinates represent approximate building entrances.

CAMPUS_DESTINATIONS = {
    "college_of_science": {
        "name": "College of Science",
        "x": 886.24,
        "y": 900.80,
    },
    "college_of_business": {
        "name": "College of Business Administration",
        "x": 1343.83,
        "y": 1244.75,
    },
    "university_library": {
        "name": "University Library",
        "x": 1209.32,
        "y": 827.81,
    },
    "bronco_student_center": {
        "name": "Bronco Student Center",
        "x": 1260.75,
        "y": 451.66,
    },
    "college_of_engineering": {
        "name": "College of Engineering",
        "x": 1123.06,
        "y": 963.85,
    },
}

DEFAULT_DESTINATION = "college_of_science"


def get_destination_coordinates(destination_id=DEFAULT_DESTINATION):
    destination = CAMPUS_DESTINATIONS[destination_id]

    return (
        destination["x"],
        destination["y"],
    )
