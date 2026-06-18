"""Render annotated output video with detections, tracking, and anomaly scores."""

from __future__ import annotations

import cv2
import numpy as np
from tqdm import tqdm

from .result import PipelineResult

COCO_SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6),
    (5, 7), (7, 9),
    (6, 8), (8, 10),
    (5, 11), (6, 12),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
]

LIMB_COLORS = [
    (255, 50, 50), (255, 50, 50), (255, 50, 50), (255, 50, 50),
    (0, 255, 255),
    (50, 255, 50), (50, 255, 50),
    (0, 165, 255), (0, 165, 255),
    (255, 255, 0), (255, 255, 0),
    (0, 255, 255),
    (255, 50, 255), (255, 50, 255),
    (50, 165, 255), (50, 165, 255),
]

COMPONENT_COLORS_BGR = {
    "crime_skelnet": (255, 150, 50),
    "video_mae": (0, 165, 255),
    "weapon_detection": (0, 0, 255),
    "paan": (0, 200, 0),
}


def render_video(
    video_path: str,
    result: PipelineResult,
    output_path: str,
) -> str:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    skelnet_meta = result.component_metadata.get("crime_skelnet", {})
    frame_tracks = skelnet_meta.get("frame_tracks", [])
    frame_bboxes = skelnet_meta.get("frame_bboxes", [])

    weapon_meta = result.component_metadata.get("weapon_detection", {})
    frame_weapon_boxes = weapon_meta.get("frame_boxes", [])

    n = min(total, result.num_frames)

    for idx in tqdm(range(n), desc="Rendering video"):
        ret, frame = cap.read()
        if not ret:
            break

        fused = float(result.fused_scores[idx]) if idx < len(result.fused_scores) else 0.0
        is_anom = bool(result.anomaly_mask[idx]) if idx < len(result.anomaly_mask) else False

        if is_anom:
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 255), -1)
            frame = cv2.addWeighted(frame, 0.85, overlay, 0.15, 0)
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 3)

        _draw_persons(frame, idx, frame_tracks, frame_bboxes, is_anom)
        _draw_weapons(frame, idx, frame_weapon_boxes)
        _draw_score_panel(frame, idx, result, w)
        _draw_timeline(frame, idx, n, result, w, h)
        _draw_anomaly_bar(frame, fused, result.threshold, w, h)
        _draw_frame_info(frame, idx, n, fps, fused, is_anom, w, h)

        out.write(frame)

    cap.release()
    out.release()
    print(f"[Video] Saved annotated video to {output_path}")
    return output_path


def _draw_persons(
    frame: np.ndarray,
    idx: int,
    frame_tracks: list,
    frame_bboxes: list,
    is_anom: bool,
) -> None:
    if idx >= len(frame_tracks):
        return

    track_dict = frame_tracks[idx]
    bbox_dict = frame_bboxes[idx] if idx < len(frame_bboxes) else {}

    for track_id, kpts in track_dict.items():
        box_color = (0, 255, 255) if is_anom else (0, 255, 0)

        if track_id in bbox_dict:
            x1, y1, x2, y2 = bbox_dict[track_id].astype(int)
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            label = f"ID:{track_id}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), box_color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        _draw_skeleton(frame, kpts)


def _draw_skeleton(frame: np.ndarray, kpts: np.ndarray) -> None:
    for i, (j1, j2) in enumerate(COCO_SKELETON):
        if kpts[j1, 2] > 0.3 and kpts[j2, 2] > 0.3:
            p1 = (int(kpts[j1, 0]), int(kpts[j1, 1]))
            p2 = (int(kpts[j2, 0]), int(kpts[j2, 1]))
            cv2.line(frame, p1, p2, LIMB_COLORS[i], 2, cv2.LINE_AA)

    for j in range(17):
        if kpts[j, 2] > 0.3:
            cv2.circle(frame, (int(kpts[j, 0]), int(kpts[j, 1])), 3, (0, 255, 255), -1)


def _draw_weapons(frame: np.ndarray, idx: int, frame_weapon_boxes: list) -> None:
    if idx >= len(frame_weapon_boxes):
        return

    for box in frame_weapon_boxes[idx]:
        x1, y1, x2, y2 = [int(v) for v in box["xyxy"]]
        conf = box["conf"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
        label = f"WEAPON {conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), (0, 0, 255), -1)
        cv2.putText(frame, label, (x1 + 3, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)


def _draw_score_panel(
    frame: np.ndarray, idx: int, result: PipelineResult, frame_w: int,
) -> None:
    n_comp = len(result.component_scores)
    if n_comp == 0:
        return

    panel_w = 270
    row_h = 22
    panel_h = 12 + row_h * (n_comp + 1) + 8
    x0 = frame_w - panel_w - 8
    y0 = 8

    roi = frame[y0:y0 + panel_h, x0:x0 + panel_w]
    if roi.size == 0:
        return
    dark = (roi * 0.35).astype(np.uint8)
    frame[y0:y0 + panel_h, x0:x0 + panel_w] = dark

    y = y0 + 16
    bar_x = x0 + 135
    bar_w = panel_w - 145

    for name, scores in result.component_scores.items():
        score = float(scores[idx]) if idx < len(scores) else 0.0
        color = COMPONENT_COLORS_BGR.get(name, (200, 200, 200))
        w_val = result.active_weights.get(name, 0)

        short = name[:11]
        cv2.putText(frame, f"{short} {score:.2f}", (x0 + 6, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

        cv2.rectangle(frame, (bar_x, y - 9), (bar_x + bar_w, y + 1), (60, 60, 60), -1)
        bar_len = max(1, int(score * bar_w))
        cv2.rectangle(frame, (bar_x, y - 9), (bar_x + bar_len, y + 1), color, -1)

        y += row_h

    fused = float(result.fused_scores[idx]) if idx < len(result.fused_scores) else 0.0
    fc = _score_to_color(fused, result.threshold)
    cv2.putText(frame, f"FUSED  {fused:.2f}", (x0 + 6, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, fc, 2, cv2.LINE_AA)
    cv2.rectangle(frame, (bar_x, y - 11), (bar_x + bar_w, y + 3), (60, 60, 60), -1)
    bar_len = max(1, int(fused * bar_w))
    cv2.rectangle(frame, (bar_x, y - 11), (bar_x + bar_len, y + 3), fc, -1)
    thresh_x = bar_x + int(result.threshold * bar_w)
    cv2.line(frame, (thresh_x, y - 13), (thresh_x, y + 5), (0, 0, 255), 2)


def _draw_anomaly_bar(
    frame: np.ndarray, fused: float, threshold: float, w: int, h: int,
) -> None:
    bar_h = 6
    y0 = h - 50
    color = _score_to_color(fused, threshold)
    bar_len = int(fused * w)
    cv2.rectangle(frame, (0, y0), (w, y0 + bar_h), (40, 40, 40), -1)
    if bar_len > 0:
        cv2.rectangle(frame, (0, y0), (bar_len, y0 + bar_h), color, -1)
    thresh_x = int(threshold * w)
    cv2.line(frame, (thresh_x, y0 - 1), (thresh_x, y0 + bar_h + 1), (0, 0, 255), 2)


def _draw_timeline(
    frame: np.ndarray, idx: int, total: int, result: PipelineResult, w: int, h: int,
) -> None:
    bar_h = 10
    y0 = h - 38

    cv2.rectangle(frame, (0, y0), (w, y0 + bar_h), (50, 50, 50), -1)

    for region in result.anomaly_regions:
        rx1 = int(region.start_frame / max(total, 1) * w)
        rx2 = int(region.end_frame / max(total, 1) * w)
        cv2.rectangle(frame, (rx1, y0), (rx2, y0 + bar_h), (0, 0, 180), -1)

    pos_x = int(idx / max(total - 1, 1) * w)
    cv2.rectangle(frame, (max(0, pos_x - 1), y0 - 1), (pos_x + 1, y0 + bar_h + 1),
                  (255, 255, 255), -1)


def _draw_frame_info(
    frame: np.ndarray, idx: int, total: int, fps: float,
    fused: float, is_anom: bool, w: int, h: int,
) -> None:
    ts = idx / fps
    status = "ANOMALY" if is_anom else "NORMAL"
    status_color = (0, 0, 255) if is_anom else (0, 200, 0)

    info = f"Frame {idx}/{total}  |  {ts:.1f}s  |  Score: {fused:.3f}"
    cv2.putText(frame, info, (8, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA)

    (tw, _), _ = cv2.getTextSize(status, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.putText(frame, status, (w - tw - 10, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2, cv2.LINE_AA)

    cv2.putText(frame, "OmniSight", (8, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)


def _score_to_color(score: float, threshold: float) -> tuple:
    if score >= threshold:
        return (0, 0, 255)
    ratio = score / max(threshold, 1e-6)
    g = int(255 * (1 - ratio))
    r = int(255 * ratio)
    return (0, g, r)
