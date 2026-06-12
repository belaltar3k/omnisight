import json
import numpy as np


def parse_alphapose_json(file_path: str) -> list[list[np.ndarray]]:
    """
    Parse a person-first AlphaPose JSON file.

    Expected structure:
        { "person_id": { "frame_id": { "keypoints": [51 floats] } } }

    Returns:
        List of frames sorted by frame ID; each frame is a list of (17, 3) arrays.
    """
    with open(file_path) as fh:
        data = json.load(fh)

    if not data:
        return []

    frame_dict: dict[int, list[np.ndarray]] = {}

    for _pid, frames in data.items():
        for fid_raw, frame_data in frames.items():
            # Normalise frame ID to int
            try:
                fid = int("".join(filter(str.isdigit, str(fid_raw))))
            except ValueError:
                continue

            kp_raw = frame_data.get("keypoints")
            if kp_raw is None:
                continue

            try:
                kp = np.array(kp_raw, dtype=np.float32)
                if kp.size != 51:
                    continue
                kp = kp.reshape(17, 3)
            except (ValueError, AttributeError):
                continue

            frame_dict.setdefault(fid, []).append(kp)

    if not frame_dict:
        return []

    return [frame_dict[fid] for fid in sorted(frame_dict)]