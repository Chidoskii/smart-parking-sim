from .base import ParkingPolicy


class AvailabilityPolicy(ParkingPolicy):
    """Choose the nearest available parking area."""

    def select_parking_area(
        self,
        vehicle_id,
        destination,
        parking_areas,
        occupancy,
    ):
        available_areas = []

        for area in parking_areas:
            area_id = area["id"]
            capacity = area["capacity"]
            occupied = occupancy.get(area_id, 0)

            if occupied >= capacity:
                continue

            available_areas.append(area)

        if not available_areas:
            return None

        # Keep the preferred area whenever it has capacity.
        for area in available_areas:
            if area["id"] == destination:
                return destination

        # Otherwise choose the lowest-cost available candidate.
        # The bridge will supply a reachable route distance.
        reachable = [
            area for area in available_areas
            if area.get("distance") is not None
        ]

        if not reachable:
            return None

        return min(
            reachable,
            key=lambda area: area["distance"],
        )["id"]
