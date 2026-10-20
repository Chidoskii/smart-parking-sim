from .baseline import BaselinePolicy
from .availability import AvailabilityPolicy
from .smart import SmartPolicy


def get_parking_policy(scenario):
    policies = {
        "baseline": BaselinePolicy,
        "availability": AvailabilityPolicy,
        "smart": SmartPolicy,
    }

    if scenario not in policies:
        raise ValueError(f"Unknown parking scenario: {scenario}")

    return policies[scenario]()