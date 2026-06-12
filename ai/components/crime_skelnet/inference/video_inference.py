"""
Single-video inference with YOLOv8x-pose + BoT-SORT tracking + CrimeSkelNet.

Usage:
    python scripts/infer.py --video test.mp4 --weights best_anomaly_skel.pth
"""

import argparse
import sys
import os

# Add the project root to sys.path so we can import as a package
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir is omnisight/ai/components/crime_skelnet/inference
project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Trick Python into treating this script as part of the package
__package__ = "ai.components.crime_skelnet.inference"

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from tqdm import tqdm
from ultralytics import YOLO

from ..config  import Config
from ..data    import compute_bone, compute_motion, compute_angle
from ..models  import CrimeSkelNet

COCO_EDGES = [
    (15, 13), (13, 11), (16, 14), (14, 12), (11, 12),
    (5, 11),  (6, 12),  (5, 6),   (5, 7),   (7, 9),
    (6, 8),   (8, 10),  (1, 2),   (0, 1),   (0, 2),
    (1, 3),   (2, 4),   (3, 5),   (4, 6),
]


# ── Preprocessing ─────────────────────────────────────────────────────────────

def preprocess_clip(raw_clip: np.ndarray, cfg: Config) -> torch.Tensor:
    """
    raw_clip: (T, M, V=17, C=3) float32 numpy array
    Returns:  (1, 5, 3, target_frames, 17, M) tensor ready for the model
    """
    joint = torch.tensor(raw_clip.transpose(3, 0, 2, 1).copy(), dtype=torch.float32)
    joint = torch.nan_to_num(joint, nan=0.0, posinf=0.0, neginf=0.0)

    # Normalise
    conf   = joint[2]
    mask   = conf > 0
    center = (joint[:2, :, 11:12, :] + joint[:2, :, 12:13, :]) / 2.0
    joint[:2] -= center

    y        = joint[1].clone()
    y[~mask] = -1e4
    h_max    = y.amax(dim=1, keepdim=True)
    y[~mask] =  1e4
    h_min    = y.amin(dim=1, keepdim=True)
    scale    = (h_max - h_min).clamp(min=1.0)
    joint[:2] /= scale.unsqueeze(0)
    joint[:2]  = joint[:2].clamp(-5.0, 5.0)

    invalid = conf.sum(dim=(0, 1)) < 1e-3
    if invalid.any():
        joint[:, :, :, invalid] = 0.0

    # Resample to target length
    C, T, V, M = joint.shape
    if T != cfg.target_frames:
        xr          = joint.permute(2, 3, 0, 1).reshape(V * M, C, T)
        xy_weighted = xr[:, :2, :] * xr[:, 2:3, :]
        xy_i        = F.interpolate(xy_weighted, size=cfg.target_frames, mode="linear", align_corners=False)
        cf_i        = F.interpolate(xr[:, 2:3, :],  size=cfg.target_frames, mode="linear", align_corners=False)
        out         = torch.cat([xy_i / (cf_i + 1e-5), cf_i], dim=1)
        joint       = out.view(V, M, C, cfg.target_frames).permute(2, 3, 0, 1)

    joint = torch.nan_to_num(joint, nan=0.0)
    order = torch.argsort(joint[0].mean(dim=(0, 1)))
    joint = joint[:, :, :, order]

    bone = compute_bone(joint)
    eff_fps = cfg.target_frames / cfg.clip_seconds

    streams = torch.stack([
        joint,
        bone,
        compute_motion(joint, eff_fps, cfg.base_fps),
        compute_motion(bone,  eff_fps, cfg.base_fps),
        compute_angle(bone),
    ], dim=0)

    return torch.nan_to_num(streams, nan=0.0).unsqueeze(0)   # (1, 5, 3, T, V, M)


def _extract_state_dict(ckpt: dict) -> dict:
    if not isinstance(ckpt, dict):
        return ckpt
    for key in ("model", "state_dict", "model_state_dict", "net", "ema"):
        if key in ckpt and isinstance(ckpt[key], dict):
            return ckpt[key]
    return ckpt


def _normalize_state_dict_keys(state_dict: dict) -> dict:
    normalized = {}
    for key, value in state_dict.items():
        k = key.replace("_orig_mod.", "")
        normalized[k] = value
    return normalized


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_skeleton(frame: np.ndarray, kpts: np.ndarray, conf_thresh: float = 0.25) -> None:
    for p1, p2 in COCO_EDGES:
        if kpts[p1, 2] > conf_thresh and kpts[p2, 2] > conf_thresh:
            cv2.line(frame, (int(kpts[p1, 0]), int(kpts[p1, 1])),
                     (int(kpts[p2, 0]), int(kpts[p2, 1])), (0, 255, 255), 2)
    for j in range(17):
        if kpts[j, 2] > conf_thresh:
            cv2.circle(frame, (int(kpts[j, 0]), int(kpts[j, 1])), 4, (0, 165, 255), -1)


def _draw_label(frame: np.ndarray, prob: float, threshold: float) -> None:
    is_anomaly = prob > threshold
    color      = (0, 0, 255) if is_anomaly else (0, 255, 0)
    text       = f"Status: {'Anomaly' if is_anomaly else 'Normal'} ({prob:.2f})"
    cv2.rectangle(frame, (10, 10), (450, 60), (0, 0, 0), -1)
    cv2.putText(frame, text, (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)


# ── Main inference pipeline ───────────────────────────────────────────────────

def run_inference(
    video_path:     str,
    model_weights:  str,
    output_path:    str,
    threshold:      float = 0.61,
) -> None:
    cfg    = Config()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load CrimeSkelNet
    print("Loading CrimeSkelNet …")
    model = CrimeSkelNet(
        num_classes=cfg.num_classes, num_streams=cfg.num_streams
    ).to(device)
    ckpt       = torch.load(model_weights, map_location=device)
    raw_state  = _extract_state_dict(ckpt)
    state_dict = _normalize_state_dict_keys(raw_state)
    incompatible = model.load_state_dict(state_dict, strict=False)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        print("⚠️  Checkpoint mismatch detected:")
        if incompatible.missing_keys:
            print(f"   Missing keys: {len(incompatible.missing_keys)}")
        if incompatible.unexpected_keys:
            print(f"   Unexpected keys: {len(incompatible.unexpected_keys)}")
    model.eval()

    # Load YOLO pose
    print("Loading YOLOv8x-pose …")
    yolo = YOLO("yolov8x-pose.pt")

    cap         = cv2.VideoCapture(video_path)
    fps         = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frames:       list[np.ndarray] = []
    frame_tracks: list[dict]       = []

    # Phase 1: extract + track
    print("Phase 1 — Extracting skeletons …")
    for _ in tqdm(range(total_frames)):
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)

        results      = yolo.track(frame, persist=True, tracker="botsort.yaml", verbose=False, conf=0.25)
        frame_dict: dict[int, np.ndarray] = {}

        if (len(results) > 0
                and results[0].boxes is not None
                and results[0].boxes.id is not None
                and results[0].keypoints is not None):
            ids  = results[0].boxes.id.cpu().numpy().astype(int)
            kpts = results[0].keypoints.data.cpu().numpy()
            for t_id, kpt in zip(ids, kpts):
                frame_dict[t_id] = kpt

        frame_tracks.append(frame_dict)
    cap.release()

    # Phase 2: sliding-window CrimeSkelNet inference
    T_total     = len(frame_tracks)
    window_size = int(cfg.clip_seconds * fps)
    step        = int(fps // 2)
    score_lists: list[list[float]] = [[] for _ in range(T_total)]

    print("Phase 2 — Running CrimeSkelNet …")
    for start in tqdm(range(0, T_total, step)):
        end = min(start + window_size, T_total)
        if end - start < 8:
            continue

        window = frame_tracks[start:end]

        # Select the top-M most-seen track IDs in this window
        id_counts: dict[int, int] = {}
        for fd in window:
            for t_id in fd:
                id_counts[t_id] = id_counts.get(t_id, 0) + 1
        top_ids = sorted(id_counts, key=lambda x: id_counts[x], reverse=True)[: cfg.max_bodies]

        if not top_ids:
            prob = 0.0
        else:
            clip = np.zeros((end - start, cfg.max_bodies, 17, 3), dtype=np.float32)
            for t_idx, fd in enumerate(window):
                for m_idx, t_id in enumerate(top_ids):
                    if t_id in fd:
                        clip[t_idx, m_idx] = fd[t_id]
                    elif t_idx > 0:
                        clip[t_idx, m_idx] = clip[t_idx - 1, m_idx]   # forward fill

            if np.std(clip[:, :, :, :2], axis=0).sum() < 3.0:
                prob = 0.0
            else:
                x_tensor = preprocess_clip(clip, cfg).to(device)
                with torch.no_grad(), torch.amp.autocast("cuda"):
                    prob = torch.softmax(model(x_tensor), dim=1)[0, 1].item()

        for i in range(start, end):
            score_lists[i].append(prob)

    frame_scores = [float(np.mean(s)) if s else 0.0 for s in score_lists]

    # Phase 3: render output
    print("Phase 3 — Rendering …")
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for t in tqdm(range(T_total)):
        frame = frames[t].copy()
        for kpts in frame_tracks[t].values():
            _draw_skeleton(frame, kpts)
        _draw_label(frame, frame_scores[t], threshold)
        writer.write(frame)

    writer.release()
    print(f"✅  Saved → {output_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video",   required=True)
    parser.add_argument("--weights", default="best_anomaly_skel.pth")
    parser.add_argument("--output",  default="output.mp4")
    parser.add_argument("--threshold", type=float, default=0.61)
    args = parser.parse_args()
    run_inference(args.video, args.weights, args.output, args.threshold)