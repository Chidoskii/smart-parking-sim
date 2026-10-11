import json
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError

BACKEND_URL = "http://localhost:5000"

PARKING_AREA = "hill_pa181138927#0"


def update_occupancy(area_id, occupied):
    url = f"{BACKEND_URL}/api/occupancy/areas/{quote(area_id, safe='')}"

    payload = json.dumps({
        "occupied": occupied
    }).encode("utf-8")

    request = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json"
        },
        method="PATCH"
    )

    try:
        with urlopen(request, timeout=5) as response:
            result = json.load(response)

            print("Backend response:")
            print(json.dumps(result, indent=2))

            return result

    except HTTPError as error:
        print(f"HTTP error: {error.code}")
        print(error.read().decode("utf-8"))

    except URLError as error:
        print(f"Connection error: {error.reason}")

    return None


def main():
    print("Testing Python → Express connection")

    result = update_occupancy(PARKING_AREA, 0)

    if result is not None:
        print("\nPython successfully communicated with Express!")
    else:
        print("\nConnection test failed.")


if __name__ == "__main__":
    main()