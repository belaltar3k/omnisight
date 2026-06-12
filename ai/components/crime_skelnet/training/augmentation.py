import random
import numpy as np
import torch
import torch.nn.functional as F


def cap_normal_class(
    index: list[dict],
    label: int,
    max_clips: int,
    seed: int | None = None,
) -> list[dict]:
    """Down-sample the dominant class to avoid extreme imbalance."""
    rng   = random.Random(seed) if seed is not None else random
    this  = [d for d in index if d["label"] == label]
    other = [d for d in index if d["label"] != label]
    if len(this) > max_clips:
        this = rng.sample(this, max_clips)
    return this + other


def class_aware_mixup(
    x: torch.Tensor,
    y: torch.Tensor,
    num_classes: int,
    alpha: float = 0.4,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Mixup that biases λ away from 0.5 when mixing across the
    normal / anomaly boundary, preserving label dominance.
    """
    B   = x.size(0)
    lam = np.random.beta(alpha, alpha, size=(B,)) if alpha > 0 else np.ones(B)
    idx = torch.randperm(B, device=x.device)

    for i in range(B):
        if y[i] == 0 and y[idx[i]] != 0:
            lam[i] = min(lam[i], 1 - lam[i])
        elif y[i] != 0 and y[idx[i]] == 0:
            lam[i] = max(lam[i], 1 - lam[i])

    lam_t  = torch.tensor(lam, dtype=x.dtype, device=x.device).view(B, 1, 1, 1, 1, 1)
    mixed  = lam_t * x + (1 - lam_t) * x[idx]
    y_oh   = F.one_hot(y, num_classes).float()
    y_soft = lam_t.view(B, 1) * y_oh + (1 - lam_t.view(B, 1)) * y_oh[idx]

    return mixed, y_soft