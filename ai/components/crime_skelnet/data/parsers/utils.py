import numpy as np


def pad_and_stack(
    poses: list[list[np.ndarray]],
    max_bodies: int = 2,
) -> np.ndarray | None:
    """
    Convert a variable-length list of per-frame body poses into a
    fixed-shape numpy array: (T, max_bodies, 17, 3).

    Returns None when the sequence is too short to be useful (<8 frames).
    """
    T = len(poses)
    if T < 8:
        return None

    out = np.zeros((T, max_bodies, 17, 3), dtype=np.float32)

    for t in range(T):
        n_bodies = min(len(poses[t]), max_bodies)
        for m in range(n_bodies):
            out[t, m] = poses[t][m]

    return out