import numpy as np
import pandas as pd


def parse_hrcrime_csv(file_path: str) -> list[list[np.ndarray]]:
    """
    Parse an HR-Crime OpenPose/AlphaPose CSV trajectory file.

    Format: each row is one frame.
      Column 0   → frame index (discarded)
      Columns 1+ → X1, Y1, X2, Y2, … (34 values for 17 joints)

    Confidence scores are absent in HR-Crime; we inject 1.0 for all joints.

    Returns:
        List of frames; each frame is a list containing one (17, 3) array.
    """
    df = pd.read_csv(file_path, header=None, sep=None, engine="python")
    poses: list[list[np.ndarray]] = []

    for _, row in df.iterrows():
        coords = row.values[1:].astype(np.float32)
        if len(coords) < 34:
            continue
        xy   = coords[:34].reshape(17, 2)
        conf = np.ones((17, 1), dtype=np.float32)
        poses.append([np.concatenate([xy, conf], axis=1)])

    return poses