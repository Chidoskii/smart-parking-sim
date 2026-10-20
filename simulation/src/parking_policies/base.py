from abc import ABC, abstractmethod


class ParkingPolicy(ABC):
    """Base interface for parking assignment strategies."""

    @abstractmethod
    def select_parking_area(
        self,
        vehicle_id,
        destination,
        parking_areas,
        occupancy,
    ):
        """
        Select a parking area for a vehicle.

        Args:
            vehicle_id: SUMO vehicle identifier.
            destination: Intended destination of the vehicle.
            parking_areas: Candidate parking area information.
            occupancy: Current occupancy information.

        Returns:
            Selected parking area ID, or None.
        """
        pass