"""
converters/ds9_roboflow.py

Dataset: weapon_dataset9_roboflow
S3 prefix: weapon_datasets/weapon_dataset9_roboflow/
Format: YOLO, 1 class (0=Gun)
Splits: train/ ONLY (no val/test provided)

Action:
  - Download train/images and train/labels
  - Class 0 (Gun) → remap to 0 (weapon)
  - Manually split: 80% train, 10% val, 10% test
"""

import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_download_prefix,
    read_yolo_label, write_yolo_label, write_empty_label,
)

DATASET_NAME = "ds9_roboflow"
S3_PREFIX    = "weapon_datasets/weapon_dataset9_roboflow/train/"

TRAIN_RATIO  = 0.80
VAL_RATIO    = 0.10
# test = remaining 10%

SEED = 42


def main():
    log.info(f"[{DATASET_NAME}] Starting (train-only source, auto-splitting)...")
    stage   = staging_dir(DATASET_NAME)
    img_dir = stage / "raw" / "images"
    lbl_dir = stage / "raw" / "labels"
    out_lbl_dir = stage / "labels_converted"

    s3_download_prefix(
        S3_PREFIX + "images/",
        img_dir,
        extensions=(".jpg", ".jpeg", ".png"),
        desc=f"{DATASET_NAME} images",
    )
    s3_download_prefix(
        S3_PREFIX + "labels/",
        lbl_dir,
        extensions=(".txt",),
        desc=f"{DATASET_NAME} labels",
    )

    image_files = sorted(img_dir.glob("*.*"))
    random.seed(SEED)
    random.shuffle(image_files)

    n = len(image_files)
    n_train = int(n * TRAIN_RATIO)
    n_val   = int(n * VAL_RATIO)

    split_assignment = (
        ["train"] * n_train +
        ["val"]   * n_val +
        ["test"]  * (n - n_train - n_val)
    )

    manifest_rows = []
    counts = {"train": [0, 0], "val": [0, 0], "test": [0, 0]}  # [pos, neg]

    for img_path, split in zip(image_files, split_assignment):
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        out_lbl  = out_lbl_dir / (img_path.stem + ".txt")

        if lbl_path.exists():
            raw_boxes = read_yolo_label(lbl_path)
            # class 0 = Gun → weapon class 0
            boxes = [(0, cx, cy, w, h) for cls, cx, cy, w, h in raw_boxes if cls == 0]
        else:
            boxes = []

        if boxes:
            write_yolo_label(out_lbl, boxes)
            counts[split][0] += 1
            is_neg = False
        else:
            write_empty_label(out_lbl)
            counts[split][1] += 1
            is_neg = True

        manifest_rows.append({
            "image_path": str(img_path),
            "label_path": str(out_lbl),
            "split": split,
            "dataset": DATASET_NAME,
            "is_negative": is_neg,
        })

    append_manifest(manifest_rows)
    for split, (pos, neg) in counts.items():
        log.info(f"  {split}: {pos} pos | {neg} neg")
    log.info(f"[{DATASET_NAME}] Done. {len(manifest_rows)} total images.")


if __name__ == "__main__":
    main()
