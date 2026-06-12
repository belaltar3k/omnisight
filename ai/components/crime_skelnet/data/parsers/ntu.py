import numpy as np
from ..taxonomy import KINECT_TO_COCO


def parse_ntu_skeleton(file_path: str) -> list[list[np.ndarray]]:
    """
    Parse a Microsoft Kinect v2 NTU RGB+D .skeleton file.

    The file maps 25 3-D joints to COCO-17 2-D joints using pixel
    coordinates (columns 5 and 6 in the joint data rows).

    Returns:
        List of frames; each frame is a list of (17, 3) arrays
        (one per tracked body).
    """
    with open(file_path, "r") as fh:
        lines = fh.readlines()

    if not lines:
        return []

    poses: list[list[np.ndarray]] = []

    try:
        num_frames = int(lines[0].strip())
    except ValueError:
        return []

    cursor = 1
    for _ in range(num_frames):
        if cursor >= len(lines):
            break

        try:
            num_bodies = int(lines[cursor].strip())
            cursor += 1
        except (ValueError, IndexError):
            break

        frame_poses: list[np.ndarray] = []

        for _ in range(num_bodies):
            try:
                cursor += 1  # skip body metadata line
                num_joints = int(lines[cursor].strip())
                cursor += 1

                coco = np.zeros((17, 3), dtype=np.float32)

                for j in range(num_joints):
                    joint_data = lines[cursor].strip().split()
                    cursor += 1

                    if j in KINECT_TO_COCO and len(joint_data) > 6:
                        coco_idx       = KINECT_TO_COCO[j]
                        coco[coco_idx, 0] = float(joint_data[5])  # pixel x
                        coco[coco_idx, 1] = float(joint_data[6])  # pixel y
                        coco[coco_idx, 2] = 1.0

                frame_poses.append(coco)

            except (ValueError, IndexError):
                break

        poses.append(frame_poses)

    return poses