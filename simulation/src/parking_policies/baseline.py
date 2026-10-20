from .base import ParkingPolicy


class BaselinePolicy(ParkingPolicy):

    def select_parking_area(
        self,
        vehicle_id,
        destination,
        parking_areas,
        occupancy,
    ):
        if not parking_areas:
            return None

        # Placeholder: choose the first candidate.
        # No real-time occupancy information is used.
        return parking_areas[0]["id"]