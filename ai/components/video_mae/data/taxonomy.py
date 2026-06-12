"""
Crime class taxonomy for the VideoMAE / CrimeTransformer component.

14 classes drawn from UCF-Crime, matching the HR-Crime taxonomy used
across the Omnisight architecture.
"""

CRIME_CLASSES: list[str] = [
    "Normal",
    "Abuse",
    "Arrest",
    "Arson",
    "Assault",
    "Burglary",
    "Explosion",
    "Fighting",
    "RoadAccidents",
    "Robbery",
    "Shooting",
    "Shoplifting",
    "Stealing",
    "Vandalism",
]

NUM_CLASSES: int = len(CRIME_CLASSES)

# Convenience: lowercase → class index (for path-based label inference)
_LOWER_TO_IDX: dict[str, int] = {c.lower(): i for i, c in enumerate(CRIME_CLASSES)}


def class_index_from_path(filepath: str) -> int:
    """
    Infer the crime class index from a file path by matching class names.
    Falls back to index 1 (first anomaly class) when no match is found.
    """
    fp_lower = filepath.lower()
    for name, idx in _LOWER_TO_IDX.items():
        if name in fp_lower:
            return idx
    return 1