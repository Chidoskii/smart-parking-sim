from .base import ParkingPolicy


class SmartPolicy(ParkingPolicy):

    DRIVING_WEIGHT = 0.25
    WALKING_WEIGHT = 0.60
    OCCUPANCY_WEIGHT = 0.15

    def select_parking_area(
        self,
        vehicle_id,
        destination,
        parking_areas,
        occupancy,
    ):
        if not parking_areas:
            return None

        max_driving = max(
            area["distance"] for area in parking_areas
        )

        max_walking = max(
            area["walking_distance"] for area in parking_areas
        )

        best_area = None
        best_cost = float("inf")

        for area in parking_areas:
            driving_score = (
                area["distance"] / max_driving
                if max_driving > 0 else 0.0
            )

            walking_score = (
                area["walking_distance"] / max_walking
                if max_walking > 0 else 0.0
            )

            capacity = area["capacity"]

            occupancy_score = (
                occupancy.get(area["id"], 0) / capacity
                if capacity > 0 else 1.0
            )

            cost = (
                self.DRIVING_WEIGHT * driving_score
                + self.WALKING_WEIGHT * walking_score
                + self.OCCUPANCY_WEIGHT * occupancy_score
            )

            if cost < best_cost:
                best_cost = cost
                best_area = area["id"]

        return best_area