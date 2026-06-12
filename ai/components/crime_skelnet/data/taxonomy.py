"""
Unified class taxonomy for Omnisight anomaly detection.

15 classes built around HR-Crime as the base, extended with
NTU RGB+D classes not covered by HR-Crime.
"""

# ── Output class names ───────────────────────────────────────────────────────
CRIME_CLASSES = ["Normal_Behavior", "Anomaly"]

# ── Source label → unified integer label ────────────────────────────────────
# 0 = Normal_Behavior  |  1 = Anomaly
LABEL_MAP: dict[str, int] = {
    # Normal sources
    "noFight":                          0,
    "NonViolence":                      0,
    "No_Gun":                           0,
    "normal":                           0,
    "non shop lifters":                 0,
    "Testing_Normal_Videos_Anomaly":    0,
    "Training_Normal_Videos_Anomaly":   0,

    # Violence / assault
    "fight":                            1,
    "Fighting":                         1,
    "Violence":                         1,
    "Assault":                          1,
    "Abuse":                            1,

    # Firearms
    "Shooting":                         1,
    "Handgun":                          1,
    "Machine_Gun":                      1,

    # Retail / property crimes
    "shoplifting":                      1,
    "Shoplifting":                      1,
    "shop lifters":                     1,
    "Robbery":                          1,
    "Snatch Theft":                     1,
    "Burglary":                         1,
    "Stealing":                         1,
    "Vandalism":                        1,

    # Public incidents
    "Arson":                            1,
    "Explosion":                        1,
    "RoadAccidents":                    1,
    "Arrest":                           1,
}

# ── NTU RGB+D action code → unified integer label ───────────────────────────
NTU_MAPPING: dict[str, int] = {
    # Melee / weapons
    "A107": 1,   # wield knife
    "A110": 1,   # shoot with gun
    # Physical assault
    "A050": 1,   # punch / slap
    "A051": 1,   # kicking
    "A052": 1,   # pushing
    # Medical emergencies (treated as anomaly)
    "A042": 1,   # staggering
    "A043": 1,   # falling down
    "A044": 1,   # headache
    "A045": 1,   # chest pain
}

# ── Kinect v2 joint index → COCO-17 joint index ─────────────────────────────
# Only the 13 joints that have a direct COCO equivalent are mapped.
KINECT_TO_COCO: dict[int, int] = {
    3:  0,   # head          → nose
    4:  5,   # left shoulder → left shoulder
    8:  6,   # right shoulder→ right shoulder
    5:  7,   # left elbow    → left elbow
    9:  8,   # right elbow   → right elbow
    6:  9,   # left wrist    → left wrist
    10: 10,  # right wrist   → right wrist
    12: 11,  # left hip      → left hip
    16: 12,  # right hip     → right hip
    13: 13,  # left knee     → left knee
    17: 14,  # right knee    → right knee
    14: 15,  # left ankle    → left ankle
    18: 16,  # right ankle   → right ankle
}