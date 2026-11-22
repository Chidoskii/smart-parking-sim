from .baseline import BaselinePolicy
from .availability import AvailabilityPolicy
from .smart import SmartPolicy
from .smart_v2 import SmartV2Policy


def get_parking_policy(scenario):
    policies = {
        "baseline": BaselinePolicy,
        "availability": AvailabilityPolicy,
        "smart": SmartPolicy,
        "smart_v2": SmartV2Policy,
    }

    if scenario not in policies:
        raise ValueError(f"Unknown parking scenario: {scenario}")

    return policies[scenario]()
