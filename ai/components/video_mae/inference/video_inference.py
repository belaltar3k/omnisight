"""
Single-video inference: VideoMAE feature extraction + CrimeTransformer.

Pipeline:
    1. Decode video with decord (sliding window, stride 8).
    2. Extract VideoMAE-Large embeddings in batches.
    3. L2-normalise → pool to 32 snippets.
    4. Run CrimeTransformer to get per-snippet anomaly scores + crime class.
    5. Plot and save the anomaly curve.

Usage:
    python inference/video_inference.py \
        --video  /path/to/video.mp4 \
        --weights /data/checkpoints/best_model.pth \
        --output  /data/output.png \
        --threshold 0.65
"""

import argparse
import os
import sys

# Add the project root to sys.path so we can import as a package
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir is omnisight/ai/components/video_mae/inference
project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Trick Python into treating this script as part of the package
__package__ = "ai.components.video_mae.inference"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from decord import VideoReader, cpu
from transformers import VideoMAEImageProcessor, VideoMAEModel

from ..config import Config
from ..data   import pool_to_snippets
from ..data.taxonomy import CRIME_CLASSES, NUM_CLASSES
from ..models import CrimeTransformer


# ── Feature extraction ────────────────────────────────────────────────────────

def extract_videomae_features(
    video_path: str,
    device:     str,
    clip_len:   int = 16,
    stride:     int = 8,
    batch_size: int = 32,
) -> tuple[np.ndarray, float, int]:
    """
    Extract per-clip VideoMAE-Large embeddings from a video file.

    Returns:
        features:     (N, 1024) float32 — one embedding per clip
        fps:          source video frame rate
        total_frames: total number of decoded frames
    """
    print("Loading VideoMAE-Large …")
    processor = VideoMAEImageProcessor.from_pretrained("MCG-NJU/videomae-large")
    extractor = VideoMAEModel.from_pretrained("MCG-NJU/videomae-large").to(device).eval()

    vr           = VideoReader(video_path, ctx=cpu(0))
    total_frames = len(vr)
    fps          = vr.get_avg_fps()
    duration     = total_frames / fps
    print(f"Duration: {duration:.2f}s  ({total_frames} frames @ {fps:.1f} FPS)")

    frame_indices = list(range(0, total_frames - clip_len + 1, stride))
    all_embs: list[np.ndarray] = []

    with torch.no_grad():
        for b_start in range(0, len(frame_indices), batch_size):
            batch_starts = frame_indices[b_start : b_start + batch_size]
            clips = []
            for s in batch_starts:
                clip = vr.get_batch(range(s, s + clip_len)).asnumpy()
                clips.append(list(clip))
            inputs = processor(clips, return_tensors="pt").pixel_values.to(device)
            embs   = extractor(inputs).last_hidden_state.mean(dim=1).cpu().numpy()
            all_embs.append(embs)

    features = np.vstack(all_embs)
    print(f"Extracted {len(features)} clips → {features.shape}")
    return features, fps, total_frames


# ── Preprocessing ─────────────────────────────────────────────────────────────

def preprocess_features(
    features:     np.ndarray,
    num_snippets: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    L2-normalise → pool to fixed snippets → compute magnitudes.

    Returns:
        feat_tensor: (1, num_snippets, 1024)
        mag_tensor:  (1, num_snippets, 1)
    """
    norms    = np.linalg.norm(features, axis=1, keepdims=True)
    features = features / (norms + 1e-6)
    features = pool_to_snippets(features, num_snippets)
    mags     = np.linalg.norm(features, axis=1, keepdims=True).astype(np.float32)

    return (
        torch.from_numpy(features).unsqueeze(0),
        torch.from_numpy(mags).unsqueeze(0),
    )


# ── Visualisation ─────────────────────────────────────────────────────────────

def save_anomaly_plot(
    scores:          np.ndarray,
    duration:        float,
    video_name:      str,
    predicted_class: str,
    output_path:     str,
    threshold:       float = 0.65,
) -> None:
    time_axis = np.linspace(0, duration, len(scores))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(time_axis, scores, color="red", linewidth=2, label="Anomaly Score")
    ax.fill_between(time_axis, scores, color="red", alpha=0.2)
    ax.axhline(y=threshold, color="black", linestyle="--", label=f"Threshold ({threshold})")
    ax.set_ylim(0, 1.0)
    ax.set_xlim(0, duration)
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Suspicion Probability")
    ax.set_title(f"AI Analysis: {video_name}\nPrediction: {predicted_class}")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Anomaly graph → {output_path}")


# ── Main inference pipeline ───────────────────────────────────────────────────

def run_inference(
    video_path:  str,
    weights:     str,
    output_path: str,
    threshold:   float = 0.65,
) -> None:
    cfg    = Config()
    device = cfg.device if torch.cuda.is_available() else "cpu"

    # ── Load model ───────────────────────────────────────────────
    print(f"Loading CrimeTransformer from {weights} …")
    model = CrimeTransformer(
        feature_dim  = cfg.feature_dim,
        num_classes  = NUM_CLASSES,
        num_snippets = cfg.num_snippets,
        d_model      = cfg.d_model,
        nhead        = cfg.nhead,
        num_layers   = cfg.num_layers,
        dropout      = cfg.dropout,
    ).to(device)

    try:
        ckpt = torch.load(weights, map_location=device, weights_only=False)
    except TypeError:
        # Older PyTorch versions do not support weights_only.
        ckpt = torch.load(weights, map_location=device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    # ── Extract features ─────────────────────────────────────────
    features, fps, total_frames = extract_videomae_features(video_path, device)
    duration                    = total_frames / fps
    feat_tensor, mag_tensor     = preprocess_features(features, cfg.num_snippets)

    feat_tensor = feat_tensor.to(device)
    mag_tensor  = mag_tensor.to(device)

    # ── Predict ──────────────────────────────────────────────────
    with torch.no_grad():
        scores, logits = model(feat_tensor, mag_tensor)

    scores = scores.squeeze(0).cpu().numpy()
    probs  = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

    # Smooth scores (matches eval protocol)
    if len(scores) >= 5:
        scores = np.convolve(scores, np.ones(5) / 5, mode="same")

    predicted_class = CRIME_CLASSES[int(probs.argmax())]
    peak_score      = float(scores.max())

    print("\n" + "=" * 50)
    print(f"PREDICTION  : {predicted_class}")
    print(f"PEAK SCORE  : {peak_score * 100:.1f}%")
    if peak_score > threshold:
        print("ALERT       : Suspicious behaviour detected!")
    print("=" * 50 + "\n")

    save_anomaly_plot(
        scores, duration,
        os.path.basename(video_path),
        predicted_class,
        output_path,
        threshold,
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VideoMAE anomaly inference")
    parser.add_argument("--video",     required=True,                   help="Input video path")
    parser.add_argument("--weights",   default="best_model.pth",        help="Model weights")
    parser.add_argument("--output",    default="anomaly_output.png",    help="Output plot path")
    parser.add_argument("--threshold", type=float, default=0.65,        help="Alert threshold")
    args = parser.parse_args()

    run_inference(args.video, args.weights, args.output, args.threshold)