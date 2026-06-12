import json
import numpy as np


def parse_yolo_json(file_path: str) -> list[list[np.ndarray]]:
    """
    Parse a frame-first YOLO-pose JSON file.

    Expected structure:
        [ { "frame_index": 0,
            "persons": [ { "keypoints_xyc": [[x, y, conf], ...] } ] } ]

    Returns:
        List of frames; each frame is a list of (17, 3) float32 arrays.
    """
    with open(file_path) as fh:
        data = json.load(fh)

    frames = data if isinstance(data, list) else [data]
    poses: list[list[np.ndarray]] = []

    for frame in frames:
        frame_poses: list[np.ndarray] = []
        for person in frame.get("persons", []):
            kp = person.get("keypoints_xyc")
            if kp is None:
                continue
            arr = np.array(kp, dtype=np.float32)
            if arr.shape == (17, 3):
                frame_poses.append(arr)
        poses.append(frame_poses)

    return poses