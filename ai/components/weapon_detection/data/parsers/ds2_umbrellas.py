"""
converters/ds2_umbrellas.py

Dataset: normal_dataset2_umbrellas
S3 prefix: normal_dataset2_umbrellas/Simuletic_Weapon_Umbrella_Dataset/
Format: YOLO (images/*.JPG, labels/*.txt)
Classes: 0=person, 1=weapon, 2=umbrella

Action:
  - Images that contain class 1 (weapon): keep weapon boxes → class 0
  - Images that contain ONLY class 2 (umbrella) and/or class 0 (person):
      → use as hard negatives (empty label)
  - This is the most valuable hard-negative set (umbrella ≈ weapon shape)

Split: All → train
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_download_prefix,
    read_yolo_label, write_yolo_label, write_empty_label, remap_classes,
)

DATASET_NAME = "ds2_umbrellas"
S3_PREFIX    = "normal_dataset2_umbrellas/Simuletic_Weapon_Umbrella_Dataset/"
TARGET_SPLIT = "train"

WEAPON_CLASS   = 1
UMBRELLA_CLASS = 2
KEEP_CLASSES   = [WEAPON_CLASS]
REMAP          = {WEAPON_CLASS: 0}


def main():
    log.info(f"[{DATASET_NAME}] Starting conversion...")
    stage     = staging_dir(DATASET_NAME)
    img_dir   = stage / "images"
    label_dir = stage / "labels"
    out_label_dir = stage / "labels_converted"

    s3_download_prefix(
        S3_PREFIX + "images/",
        img_dir,
        extensions=(".jpg", ".jpeg", ".png", ".JPG"),
        desc=f"{DATASET_NAME} images",
    )
    s3_download_prefix(
        S3_PREFIX + "labels/",
        label_dir,
        extensions=(".txt",),
        desc=f"{DATASET_NAME} labels",
    )

    image_files  = sorted(img_dir.glob("*.*"))
    manifest_rows = []
    n_weapon = 0
    n_hard_neg = 0

    for img_path in image_files:
        lbl_path = label_dir / (img_path.stem + ".txt")
        out_lbl  = out_label_dir / (img_path.stem + ".txt")

        if lbl_path.exists():
            boxes = read_yolo_label(lbl_path)
            weapon_boxes = remap_classes(boxes, KEEP_CLASSES, REMAP)
            has_umbrella = any(b[0] == UMBRELLA_CLASS for b in boxes)
        else:
            weapon_boxes = []
            has_umbrella = False

        if weapon_boxes:
            # Positive: write weapon boxes
            write_yolo_label(out_lbl, weapon_boxes)
            n_weapon += 1
            is_neg = False
        else:
            # Hard negative: umbrella-only or person-only image
            write_empty_label(out_lbl)
            n_hard_neg += 1
            is_neg = True

        manifest_rows.append({
            "image_path": str(img_path),
            "label_path": str(out_lbl),
            "split": TARGET_SPLIT,
            "dataset": DATASET_NAME,
            "is_negative": is_neg,
        })

    append_manifest(manifest_rows)
    log.info(
        f"[{DATASET_NAME}] Done. "
        f"{n_weapon} weapon images | {n_hard_neg} hard negatives (umbrellas) → train"
    )


if __name__ == "__main__":
    main()
