"""
RTFMLoss: Multiple Instance Learning ranking loss.

Implements the RTFM (Robust Temporal Feature Magnitude) loss that forces
the top-K snippets of anomaly videos to score higher than the top-K
snippets of normal videos, with smoothness and sparsity regularisation.
"""

import torch
import torch.nn as nn


class RTFMLoss(nn.Module):
    """
    MIL ranking loss with magnitude-aware top-K selection.

    Args:
        margin:        minimum separation between anomaly and normal scores.
        lambda_smooth: weight for temporal smoothness penalty.
        lambda_sparse: weight for score sparsity penalty.
        k:             number of top snippets used per video.
    """

    def __init__(
        self,
        margin:        float = 0.1,
        lambda_smooth: float = 0.005,
        lambda_sparse: float = 0.005,
        k:             int   = 3,
    ):
        super().__init__()
        self.margin        = margin
        self.lambda_smooth = lambda_smooth
        self.lambda_sparse = lambda_sparse
        self.k             = k

    def forward(
        self,
        scores:       torch.Tensor,   # (B, T)  anomaly scores
        magnitudes:   torch.Tensor,   # (B, T, 1)
        video_labels: torch.Tensor,   # (B,)  float 0/1
    ) -> torch.Tensor:
        mags  = magnitudes.squeeze(-1)                              # (B, T)
        a_idx = (video_labels == 1).nonzero(as_tuple=True)[0]
        n_idx = (video_labels == 0).nonzero(as_tuple=True)[0]

        if len(a_idx) == 0 or len(n_idx) == 0:
            return torch.tensor(0.0, device=scores.device, requires_grad=True)

        def _topk_mean(idx_list: torch.Tensor) -> torch.Tensor:
            vals = []
            for i in idx_list:
                s        = scores[i]
                m        = mags[i]
                weighted = s * (m / (m.max() + 1e-6))
                k_actual = min(self.k, len(weighted))
                vals.append(torch.topk(weighted, k_actual).values.mean())
            return torch.stack(vals)

        a_scores = _topk_mean(a_idx)   # (n_anomaly,)
        n_scores = _topk_mean(n_idx)   # (n_normal,)

        # Pairwise ranking loss
        ranking = torch.clamp(
            self.margin - a_scores.unsqueeze(1) + n_scores.unsqueeze(0),
            min=0.0,
        ).mean()

        # Temporal regularisation on anomaly videos only
        smooth = torch.tensor(0.0, device=scores.device)
        sparse = torch.tensor(0.0, device=scores.device)

        for i in a_idx:
            s = scores[i]
            if len(s) > 1:
                smooth = smooth + (torch.diff(s) ** 2).mean()
            sparse = sparse + s.mean()

        n_anomaly = len(a_idx)
        smooth    = smooth / n_anomaly
        sparse    = sparse / n_anomaly

        return ranking + self.lambda_smooth * smooth + self.lambda_sparse * sparse