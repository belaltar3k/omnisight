"""
Building blocks for the CrimeTransformer.

MultiScaleTemporalConv — parallel conv1d at 3 temporal scales.
MagnitudeAttention      — RTFM-style feature-magnitude gating.
"""

import torch
import torch.nn as nn


class MultiScaleTemporalConv(nn.Module):
    """
    Parallel 1-D convolutions at kernel sizes 1, 3, and 5 to capture
    local, short-range, and mid-range temporal patterns simultaneously.

    Input:  (B, T, in_dim)
    Output: (B, T, out_dim)
    """

    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        branch   = out_dim // 3
        leftover = out_dim - branch * 3      # absorb rounding into conv5 branch

        self.conv1 = nn.Conv1d(in_dim, branch,            kernel_size=1, padding=0)
        self.conv3 = nn.Conv1d(in_dim, branch,            kernel_size=3, padding=1)
        self.conv5 = nn.Conv1d(in_dim, branch + leftover, kernel_size=5, padding=2)
        self.norm  = nn.LayerNorm(out_dim)
        self.act   = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        xt  = x.transpose(1, 2)                                   # (B, in_dim, T)
        out = torch.cat(
            [self.conv1(xt), self.conv3(xt), self.conv5(xt)], dim=1
        ).transpose(1, 2)                                          # (B, T, out_dim)
        return self.act(self.norm(out))


class MagnitudeAttention(nn.Module):
    """
    RTFM-style gating: projects per-snippet L2 magnitude to a
    d_model-dimensional gate and multiplies it element-wise with
    the feature map.

    Anomalous snippets tend to have higher VideoMAE feature magnitude,
    so this module learns to up-weight suspicious regions.

    Input:
        x:          (B, T, d_model)
        magnitudes: (B, T, 1)
    Output:
        (B, T, d_model)
    """

    def __init__(self, d_model: int):
        super().__init__()
        self.mag_proj = nn.Sequential(
            nn.Linear(1, 32),
            nn.ReLU(inplace=True),
            nn.Linear(32, d_model),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor, magnitudes: torch.Tensor) -> torch.Tensor:
        return x * self.mag_proj(magnitudes)