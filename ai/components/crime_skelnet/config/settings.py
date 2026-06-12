import os
from dataclasses import dataclass


@dataclass
class Config:
    # ── Paths ────────────────────────────────────────────────────
    data_root:       str   = "/data/datasets"
    unified_dir:     str   = "/data/unified_datasets"
    checkpoint_dir:  str   = "/data/checkpoints"

    # ── Clip representation ──────────────────────────────────────
    clip_seconds:    float = 4.0
    target_frames:   int   = 32
    num_joints:      int   = 17
    max_bodies:      int   = 2
    base_fps:        float = 30.0

    # ── Model architecture ───────────────────────────────────────
    num_classes:     int   = 2
    num_streams:     int   = 5
    base_channels:   int   = 64
    drop_path_rate:  float = 0.1

    # ── Training schedule ────────────────────────────────────────
    epochs:          int   = 80
    batch_size:      int   = 32
    accum_steps:     int   = 2
    lr:              float = 0.0003
    weight_decay:    float = 1e-4
    warmup_pct:      float = 0.15
    grad_clip:       float = 0.5

    # ── Data balancing ───────────────────────────────────────────
    max_normal_clips: int  = 15000

    # ── Regularisation ───────────────────────────────────────────
    ema_decay:       float = 0.995
    mixup_alpha:     float = 0.4
    label_smoothing: float = 0.10
    focal_gamma:     float = 2.0

    # ── Augmentation flags ───────────────────────────────────────
    aug_flip:        bool  = True
    aug_rotate:      bool  = True
    aug_scale:       bool  = True
    aug_joint_mask:  bool  = True

    # ── Evaluation ───────────────────────────────────────────────
    val_num_clips:   int   = 3

    # ── Misc ─────────────────────────────────────────────────────
    patience:        int   = 35
    seed:            int   = 42
    num_workers:     int   = 8
    use_grad_ckpt:   bool  = False
    compile_mode:    str   = "default"
    compile_model:   bool  = False
    use_bf16:        bool  = True