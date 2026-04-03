import random


def choose_interval_seconds(raw_value):
    """Return either a fixed delay or a random value within a configured range."""
    if isinstance(raw_value, (list, tuple)):
        if len(raw_value) != 2:
            raise ValueError("Configured interval ranges must contain exactly two values.")
        return random.uniform(float(raw_value[0]), float(raw_value[1]))
    return float(raw_value)
