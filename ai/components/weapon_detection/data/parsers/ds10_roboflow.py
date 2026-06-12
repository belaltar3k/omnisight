"""
converters/ds10_roboflow.py

Dataset: weapon_dataset10_roboflow
S3 prefix: weapon_datasets/weapon_dataset10_roboflow/
Format: YOLO, 2 classes: 0='0' (unknown/background), 1=weapons
Splits: train/, valid/, test/

Action:
  - Keep ONLY class 1 (weapons) → remap to 0
  - Drop class 0 entirely (it's a catch-all non-weapon class)
  - Images where all boxes are class 0 → treated as negatives (empty label)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_download_prefix,
    read_yolo_label, write_yolo_label, write_empty_label,
    remap_classes,
)

DATASET_NAME = "ds10_roboflow"
S3_PREFIX    = "weapon_datasets/weapon_dataset10_roboflow/"

SPLIT_MAP = {
    "train": "train",
    "valid": "val",
    "test":  "test",
}

KEEP_CLASSES = [1]   # only weapons class
REMAP        = {1: 0}


def process_split(s3_split: str, our_split: str, stage: Path) -> list:
    img_dir = stage / s3_split / "images"
    lbl_dir = stage / s3_split / "labels"
    out_lbl_dir = stage / s3_split / "labels_converted"

    s3_download_prefix(
        S3_PREFIX + s3_split + "/images/",
        img_dir,
        extensions=(".jpg", ".jpeg", ".png"),
        desc=f"{DATASET_NAME}/{s3_split} images",
    )
    s3_download_prefix(
        S3_PREFIX + s3_split + "/labels/",
        lbl_dir,
        extensions=(".txt",),
        desc=f"{DATASET_NAME}/{s3_split} labels",
    )

    manifest_rows = []
    n_pos = n_neg = 0

    for img_path in sorted(img_dir.glob("*.*")):
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        out_lbl  = out_lbl_dir / (img_path.stem + ".txt")

        if lbl_path.exists():
            raw_boxes = read_yolo_label(lbl_path)
            # Only keep boxes with 5 fields — filter out OBB/polygon lines silently
            valid_boxes = [b for b in raw_boxes if len(b) == 5]
            boxes = remap_classes(valid_boxes, KEEP_CLASSES, REMAP)
        else:
            boxes = []

        if boxes:
            write_yolo_label(out_lbl, boxes)
            n_pos += 1
            is_neg = False
        else:
            write_empty_label(out_lbl)
            n_neg += 1
            is_neg = True

        manifest_rows.append({
            "image_path": str(img_path),
            "label_path": str(out_lbl),
            "split": our_split,
            "dataset": DATASET_NAME,
            "is_negative": is_neg,
        })

    log.info(f"  {s3_split} → {our_split}: {n_pos} pos | {n_neg} neg")
    return manifest_rows


def main():
    log.info(f"[{DATASET_NAME}] Starting (keep weapon class only)...")
    stage = staging_dir(DATASET_NAME)
    all_rows = []
    for s3_split, our_split in SPLIT_MAP.items():
        rows = process_split(s3_split, our_split, stage)
        all_rows.extend(rows)
    append_manifest(all_rows)
    log.info(f"[{DATASET_NAME}] Done. {len(all_rows)} images.")


if __name__ == "__main__":
    main()
