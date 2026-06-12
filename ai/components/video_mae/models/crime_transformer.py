"""
CrimeTransformer: VideoMAE-feature-based anomaly detector.

Architecture summary
────────────────────
1. MultiScaleTemporalConv   — project (B, T, 1024) → (B, T, d_model)
2. MagnitudeAttention       — re-weight by feature magnitude (RTFM)
3. Positional embedding     — learned, fixed length
4. TransformerEncoder       — 4-layer, pre-norm, GELU, 8 heads
5. anomaly_head             — per-snippet score ∈ [0, 1]
6. class_head               — global magnitude-pooled class logits
"""

import torch
import torch.nn as nn

from .blocks import MagnitudeAttention, MultiScaleTemporalConv


class CrimeTransformer(nn.Module):
    """
    Input:
        features:   (B, T, feature_dim)   — L2-normalised VideoMAE embeddings
        magnitudes: (B, T, 1)             — per-snippet L2 norms

    Output:
        anomaly_scores: (B, T)     — per-snippet suspicion probability
        class_logits:   (B, C)     — crime type logits
    """

    def __init__(
        self,
        feature_dim:  int   = 1024,
        num_classes:  int   = 14,
        num_snippets: int   = 32,
        d_model:      int   = 512,
        nhead:        int   = 8,
        num_layers:   int   = 4,
        dropout:      float = 0.3,
    ):
        super().__init__()
        self.num_snippets = num_snippets

        # ── Projection ───────────────────────────────────────────
        self.multiscale = MultiScaleTemporalConv(feature_dim, d_model)
        self.mag_attn   = MagnitudeAttention(d_model)
        self.dropout    = nn.Dropout(dropout)

        # ── Positional embedding ─────────────────────────────────
        self.pos_embed = nn.Embedding(num_snippets + 10, d_model)

        # ── Transformer encoder ──────────────────────────────────
        encoder_layer = nn.TransformerEncoderLayer(
            d_model        = d_model,
            nhead          = nhead,
            dim_feedforward = d_model * 4,
            dropout        = dropout,
            activation     = "gelu",
            batch_first    = True,
            norm_first     = True,    # pre-norm (more stable)
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers           = num_layers,
            enable_nested_tensor = False,
        )

        # ── Anomaly scoring head (per-snippet) ───────────────────
        self.anomaly_head = nn.Sequential(
            nn.Linear(d_model, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, 64),
            nn.GELU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

        # ── Crime classification head (video-level) ───────────────
        self.class_head = nn.Sequential(
            nn.Linear(d_model, 512),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Dropout(dropout / 2),
            nn.Linear(256, num_classes),
        )

        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, (nn.Linear, nn.Conv1d)):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(
        self,
        features:   torch.Tensor,
        magnitudes: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        B, T, _ = features.shape

        x = self.multiscale(features)                        # (B, T, d_model)
        x = self.mag_attn(x, magnitudes)
        x = self.dropout(x)

        pos = torch.arange(T, device=features.device).unsqueeze(0)
        x   = x + self.pos_embed(pos)

        x = self.transformer(x)                              # (B, T, d_model)

        # Per-snippet anomaly scores
        anomaly_scores = self.anomaly_head(x).squeeze(-1)   # (B, T)

        # Magnitude-weighted global pool for classification
        mag_weights  = magnitudes / (magnitudes.sum(dim=1, keepdim=True) + 1e-6)
        pooled       = (x * mag_weights).sum(dim=1)          # (B, d_model)
        class_logits = self.class_head(pooled)               # (B, C)

        return anomaly_scores, class_logits