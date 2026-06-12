import torch
import torch.nn as nn
import torch.nn.functional as F


class SoftFocalLoss(nn.Module):
    """
    Label-smoothed focal loss.

    Combines focal weighting (down-weights easy examples) with
    label smoothing (prevents overconfident predictions).
    """

    def __init__(self, gamma: float = 2.0, smoothing: float = 0.1):
        super().__init__()
        self.gamma     = gamma
        self.smoothing = smoothing

    def forward(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
    ) -> torch.Tensor:
        C = logits.size(-1)

        if targets.dim() == 1:
            targets = F.one_hot(targets, C).float()

        targets  = (1 - self.smoothing) * targets + self.smoothing / C
        log_p    = F.log_softmax(logits, dim=-1)
        pt       = log_p.exp()
        focal_w  = (1 - pt).clamp(min=0.0) ** self.gamma

        return -(focal_w * log_p * targets).sum(-1).mean()