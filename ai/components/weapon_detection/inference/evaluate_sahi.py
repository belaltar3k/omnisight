"""
phase3/evaluate_sahi.py

SAHI (Sliced Aided Hyper Inference) evaluation on the test split.

Why SAHI matters for CCTV weapon detection:
  - Standard YOLO inference at 1280px still misses weapons in high-res frames
    where weapons occupy < 1% of the image (e.g. 4K CCTV at 50m distance)
  - SAHI slices the full frame into overlapping tiles, runs inference on each,
    then merges predictions with NMS
  - Typically improves small-object mAP by 15-30 points over standard inference
  - This is what separates a production model from a research demo

This script:
  1. Evaluates best.pt with STANDARD inference → baseline metrics
  2. Evaluates best.pt with SAHI tiled inference → production metrics
  3. Computes: mAP50, mAP50-95, precision, recall, F1
  4. Generates a comparison report

Tile configs tested:
  - 640×640 tiles, 20% overlap  (fast)
  - 1280×1280 tiles, 20% overlap (accurate)
  - Auto-slice (SAHI selects tile size based on image dims)
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import log, BASE_OUT

RUNS_DIR    = Path("/data/runs/weapon_detection")
REPORT_PATH = BASE_OUT / "phase3_evaluation_report.json"
IMAGE_EXTS  = {".jpg", ".jpeg", ".png"}


# ── COCO-format ground truth builder ─────────────────────────────────────────

def build_coco_gt(split: str = "test") -> Tuple[dict, List[Path]]:
    """
    Build COCO-format ground truth dict from YOLO labels in the test split.
    Returns (coco_gt_dict, list_of_image_paths)
    """
    from PIL import Image as PILImage

    img_dir = BASE_OUT / split / "images"
    lbl_dir = BASE_OUT / split / "labels"

    images_info = []
    annotations  = []
    image_paths  = []
    ann_id       = 1

    img_files = sorted(
        f for f in img_dir.glob("*.*")
        if f.suffix.lower() in IMAGE_EXTS
    )

    for img_id, img_path in enumerate(img_files, start=1):
        try:
            with PILImage.open(img_path) as im:
                W, H = im.size
        except Exception:
            continue

        images_info.append({
            "id":        img_id,
            "file_name": img_path.name,
            "width":     W,
            "height":    H,
        })
        image_paths.append(img_path)

        lbl_path = lbl_dir / (img_path.stem + ".txt")
        if not lbl_path.exists():
            continue

        for line in lbl_path.read_text().strip().splitlines():
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            _, cx, cy, nw, nh = [float(x) for x in parts]
            # Convert YOLO → COCO [x, y, w, h] absolute
            x = (cx - nw / 2) * W
            y = (cy - nh / 2) * H
            w = nw * W
            h = nh * H
            annotations.append({
                "id":           ann_id,
                "image_id":     img_id,
                "category_id":  1,
                "bbox":         [x, y, w, h],
                "area":         w * h,
                "iscrowd":      0,
            })
            ann_id += 1

    coco_gt = {
        "images":      images_info,
        "annotations": annotations,
        "categories":  [{"id": 1, "name": "weapon", "supercategory": "object"}],
    }
    return coco_gt, image_paths


# ── Standard inference evaluation ────────────────────────────────────────────

def evaluate_standard(model_path: Path, data_yaml: Path) -> dict:
    """Run standard YOLO val on test split."""
    log.info("  Running standard YOLO evaluation...")
    from ultralytics import YOLO

    model   = YOLO(str(model_path))
    metrics = model.val(
        data=str(data_yaml),
        split="test",
        imgsz=1280,
        batch=8,
        conf=0.001,    # Low conf for mAP calculation
        iou=0.6,
        device=0,
        verbose=False,
        plots=True,
        save_json=True,
    )

    return {
        "mAP50":    round(float(metrics.box.map50),    4),
        "mAP50_95": round(float(metrics.box.map),      4),
        "precision": round(float(metrics.box.mp),      4),
        "recall":    round(float(metrics.box.mr),      4),
        "f1":        round(
            2 * float(metrics.box.mp) * float(metrics.box.mr)
            / max(float(metrics.box.mp) + float(metrics.box.mr), 1e-9),
            4
        ),
    }


# ── SAHI tiled inference evaluation ──────────────────────────────────────────

def evaluate_sahi(
    model_path: Path,
    image_paths: List[Path],
    coco_gt: dict,
    slice_height: int = 640,
    slice_width:  int = 640,
    overlap_ratio: float = 0.2,
    conf: float = 0.25,
) -> dict:
    """
    Run SAHI tiled inference and compute mAP via pycocotools.
    """
    try:
        from sahi import AutoDetectionModel
        from sahi.predict import get_sliced_prediction
        from sahi.utils.coco import Coco
    except ImportError:
        log.error("SAHI not installed. Run: pip install sahi")
        return {}

    try:
        from pycocotools.coco import COCO
        from pycocotools.cocoeval import COCOeval
    except ImportError:
        log.error("pycocotools not installed. Run: pip install pycocotools")
        return {}

    import tempfile, json
    import numpy as np

    log.info(
        f"  Running SAHI evaluation "
        f"(tile={slice_height}×{slice_width}, overlap={overlap_ratio:.0%})..."
    )

    # Load SAHI detection model
    detection_model = AutoDetectionModel.from_pretrained(
        model_type="ultralytics",
        model_path=str(model_path),
        confidence_threshold=conf,
        device="cuda:0",
    )

    # Build image_id lookup
    fname_to_id = {img["file_name"]: img["id"] for img in coco_gt["images"]}

    # Run SAHI inference on all test images
    dt_anns = []
    dt_id   = 1
    t0      = time.time()

    for img_path in image_paths:
        img_id = fname_to_id.get(img_path.name)
        if img_id is None:
            continue

        try:
            result = get_sliced_prediction(
                str(img_path),
                detection_model,
                slice_height=slice_height,
                slice_width=slice_width,
                overlap_height_ratio=overlap_ratio,
                overlap_width_ratio=overlap_ratio,
                perform_standard_pred=True,   # also run full-image inference
                postprocess_type="NMM",        # Non-Maximum Merging (better than NMS for SAHI)
                postprocess_match_threshold=0.5,
                verbose=0,
            )
        except Exception as e:
            log.warning(f"  SAHI error on {img_path.name}: {e}")
            continue

        for obj_pred in result.object_prediction_list:
            bbox = obj_pred.bbox
            x1, y1, x2, y2 = bbox.minx, bbox.miny, bbox.maxx, bbox.maxy
            w, h = x2 - x1, y2 - y1
            dt_anns.append({
                "id":           dt_id,
                "image_id":     img_id,
                "category_id":  1,
                "bbox":         [x1, y1, w, h],
                "score":        obj_pred.score.value,
                "area":         w * h,
            })
            dt_id += 1

    elapsed = time.time() - t0
    fps = len(image_paths) / max(elapsed, 1)
    log.info(f"  SAHI inference: {len(image_paths)} images in {elapsed:.1f}s ({fps:.1f} img/s)")

    # Evaluate with pycocotools
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as gt_f:
        json.dump(coco_gt, gt_f)
        gt_path = gt_f.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as dt_f:
        json.dump(dt_anns, dt_f)
        dt_path = dt_f.name

    coco_eval_gt = COCO(gt_path)
    coco_eval_dt = coco_eval_gt.loadRes(dt_path)
    cocoeval     = COCOeval(coco_eval_gt, coco_eval_dt, "bbox")
    cocoeval.evaluate()
    cocoeval.accumulate()
    cocoeval.summarize()

    # Extract metrics
    stats = cocoeval.stats
    map50_95 = float(stats[0])
    map50    = float(stats[1])

    # Compute precision/recall at best F1 threshold
    precision_arr = cocoeval.eval["precision"]  # [T, R, K, A, M]
    recall_arr    = cocoeval.eval["recall"]

    # mAP@0.5 precision/recall curve
    p_at_50  = precision_arr[0, :, 0, 0, -1]  # IoU=0.5, all areas, max det=100
    r_thresh = np.linspace(0, 1, 101)

    valid_mask = p_at_50 > -1
    if valid_mask.any():
        p_vals = p_at_50[valid_mask]
        r_vals = r_thresh[valid_mask]
        f1_vals = 2 * p_vals * r_vals / np.maximum(p_vals + r_vals, 1e-9)
        best_idx = np.argmax(f1_vals)
        best_p   = float(p_vals[best_idx])
        best_r   = float(r_vals[best_idx])
        best_f1  = float(f1_vals[best_idx])
    else:
        best_p = best_r = best_f1 = 0.0

    # Cleanup temp files
    Path(gt_path).unlink(missing_ok=True)
    Path(dt_path).unlink(missing_ok=True)

    return {
        "mAP50":         round(map50,    4),
        "mAP50_95":      round(map50_95, 4),
        "precision":     round(best_p,   4),
        "recall":        round(best_r,   4),
        "f1":            round(best_f1,  4),
        "total_detections": len(dt_anns),
        "inference_fps": round(fps, 2),
        "tile_size":     f"{slice_height}x{slice_width}",
        "overlap":       overlap_ratio,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main(model_version: str = "v2_hardneg"):
    log.info(f"\n{'='*60}")
    log.info(f"  PHASE 3 EVALUATION — SAHI vs Standard")
    log.info(f"  Model: {model_version}")
    log.info(f"{'='*60}\n")

    # Find weights
    candidates = [
        RUNS_DIR / model_version / "weights" / "best.pt",
        RUNS_DIR / "v1_baseline"  / "weights" / "best.pt",
    ]
    model_path = next((c for c in candidates if c.exists()), None)
    if model_path is None:
        log.error(f"No weights found. Checked:\n" + "\n".join(str(c) for c in candidates))
        return

    log.info(f"Using weights: {model_path}")
    data_yaml = BASE_OUT / "data.yaml"

    report = {
        "model_path":  str(model_path),
        "model_version": model_version,
        "timestamp":   time.strftime("%Y-%m-%d %Human:%M:%S"),
    }

    # ── 1. Build ground truth ────────────────────────────────────────────────
    log.info("\nBuilding COCO ground truth from test split...")
    coco_gt, image_paths = build_coco_gt("test")
    n_images = len(image_paths)
    n_boxes  = len(coco_gt["annotations"])
    log.info(f"  {n_images} test images | {n_boxes} ground truth boxes")
    report["test_images"] = n_images
    report["test_gt_boxes"] = n_boxes

    # ── 2. Standard inference ────────────────────────────────────────────────
    log.info("\n── Standard Inference ──")
    try:
        std_metrics = evaluate_standard(model_path, data_yaml)
        report["standard"] = std_metrics
        log.info(f"  mAP50:      {std_metrics['mAP50']:.4f}")
        log.info(f"  mAP50-95:   {std_metrics['mAP50_95']:.4f}")
        log.info(f"  Precision:  {std_metrics['precision']:.4f}")
        log.info(f"  Recall:     {std_metrics['recall']:.4f}")
        log.info(f"  F1:         {std_metrics['f1']:.4f}")
    except Exception as e:
        log.error(f"Standard evaluation failed: {e}")
        report["standard"] = {"error": str(e)}

    # ── 3. SAHI tiled inference ──────────────────────────────────────────────
    sahi_configs = [
        {"slice_height": 640,  "slice_width": 640,  "overlap_ratio": 0.2, "label": "SAHI_640"},
        {"slice_height": 1280, "slice_width": 1280, "overlap_ratio": 0.2, "label": "SAHI_1280"},
    ]
    report["sahi"] = {}

    for cfg in sahi_configs:
        label = cfg.pop("label")
        log.info(f"\n── {label} ──")
        try:
            sahi_metrics = evaluate_sahi(model_path, image_paths, coco_gt, **cfg)
            report["sahi"][label] = sahi_metrics
            if sahi_metrics:
                log.info(f"  mAP50:      {sahi_metrics['mAP50']:.4f}")
                log.info(f"  mAP50-95:   {sahi_metrics['mAP50_95']:.4f}")
                log.info(f"  Precision:  {sahi_metrics['precision']:.4f}")
                log.info(f"  Recall:     {sahi_metrics['recall']:.4f}")
                log.info(f"  F1:         {sahi_metrics['f1']:.4f}")
                log.info(f"  FPS:        {sahi_metrics.get('inference_fps', 'N/A')}")
        except Exception as e:
            log.error(f"{label} evaluation failed: {e}")
            report["sahi"][label] = {"error": str(e)}

    # ── 4. Comparison table ──────────────────────────────────────────────────
    log.info("\n" + "="*60)
    log.info("  FINAL COMPARISON")
    log.info("="*60)
    log.info(f"  {'Method':<20} {'mAP50':>8} {'mAP50-95':>10} {'F1':>8} {'Recall':>8}")
    log.info(f"  {'-'*20} {'-'*8} {'-'*10} {'-'*8} {'-'*8}")

    std = report.get("standard", {})
    if std and "mAP50" in std:
        log.info(
            f"  {'Standard 1280px':<20} "
            f"{std['mAP50']:>8.4f} "
            f"{std['mAP50_95']:>10.4f} "
            f"{std['f1']:>8.4f} "
            f"{std['recall']:>8.4f}"
        )

    for label, metrics in report.get("sahi", {}).items():
        if "mAP50" in metrics:
            log.info(
                f"  {label:<20} "
                f"{metrics['mAP50']:>8.4f} "
                f"{metrics['mAP50_95']:>10.4f} "
                f"{metrics['f1']:>8.4f} "
                f"{metrics['recall']:>8.4f}"
            )

    # ── 5. Save report ───────────────────────────────────────────────────────
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    log.info(f"\nReport saved: {REPORT_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-version", default="v2_hardneg",
                        help="Training run name under /data/runs/weapon_detection/")
    args = parser.parse_args()
    main(model_version=args.model_version)
