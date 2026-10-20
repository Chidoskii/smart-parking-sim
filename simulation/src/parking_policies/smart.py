from .base import ParkingPolicy


class SmartPolicy(ParkingPolicy):

    def select_parking_area(
        self,
        vehicle_id,
        destination,
        parking_areas,
        occupancy,
    ):
        # Placeholder until weighted optimization is implemented.
        return None