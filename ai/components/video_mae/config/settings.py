import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # ── Paths ────────────────────────────────────────────────────
    feature_dir:    str   = "/data/UCF_Features"
    anno_file:      str   = (
        "/data/UCF_Extracted/annotations/"
        "Temporal_Anomaly_Annotation_for_Testing_Videos.txt"
    )
    checkpoint_dir: str   = "/data/checkpoints"
    log_dir:        str   = "/data/runs"

    # ── Feature representation ───────────────────────────────────
    feature_dim:    int   = 1024
    num_snippets:   int   = 32       # fixed temporal resolution (RTFM/MGFN standard)

    # ── Model architecture ───────────────────────────────────────
    d_model:        int   = 512
    nhead:          int   = 8
    num_layers:     int   = 4
    dropout:        float = 0.3

    # ── Training schedule ────────────────────────────────────────
    epochs:         int   = 100
    batch_size:     int   = 32
    lr:             float = 1e-4
    weight_decay:   float = 1e-4
    warmup_epochs:  int   = 10
    patience:       int   = 20

    # ── Loss weights ─────────────────────────────────────────────
    cls_loss_max_weight:  float = 0.3
    label_smoothing:      float = 0.1
    mil_margin:           float = 0.1
    mil_lambda_smooth:    float = 0.005
    mil_lambda_sparse:    float = 0.005
    mil_top_k:            int   = 3

    # ── Misc ─────────────────────────────────────────────────────
    seed:           int   = 42
    num_workers:    int   = 4
    device:         str   = "cuda"   