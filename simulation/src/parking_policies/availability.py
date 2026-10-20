from .base import ParkingPolicy


class AvailabilityPolicy(ParkingPolicy):

    def select_parking_area(
        self,
        vehicle_id,
        destination,
        parking_areas,
        occupancy,
    ):
        for area in parking_areas:
            area_id = area["id"]
            capacity = area["capacity"]
            occupied = occupancy.get(area_id, 0)

            if occupied < capacity:
                return area_id

        return None