"""
converters/ds1_cctv_weapon.py

Dataset: weapon_dataset1_cctv_weapon
S3 prefix: weapon_datasets/weapon_dataset1_cctv_weapon/Dataset/
Format: YOLO (images/*.png, labels/*.txt)
Classes: 0=person, 1=weapon
Action: Keep class 1 only → remap to 0 (weapon)
Split: All → train (141 images total, small dataset)
"""

import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_download_prefix, s3_list_objects,
    read_yolo_label, write_yolo_label, remap_classes,
    BUCKET,
)

DATASET_NAME = "ds1_cctv_weapon"
S3_PREFIX    = "weapon_datasets/weapon_dataset1_cctv_weapon/Dataset/"
TARGET_SPLIT = "train"

# Class mapping: original → new
# 0=person (DROP), 1=weapon → 0
KEEP_CLASSES = [1]
REMAP        = {1: 0}


def main():
    log.info(f"[{DATASET_NAME}] Starting conversion...")
    stage = staging_dir(DATASET_NAME)

    # ── Download ───────────────────────────────────────────────────────────────
    img_dir   = stage / "images"
    label_dir = stage / "labels"

    s3_download_prefix(
        S3_PREFIX + "images/",
        img_dir,
        extensions=(".png", ".jpg", ".jpeg"),
        desc=f"{DATASET_NAME} images",
    )
    s3_download_prefix(
        S3_PREFIX + "labels/",
        label_dir,
        extensions=(".txt",),
        desc=f"{DATASET_NAME} labels",
    )

    # ── Convert labels ─────────────────────────────────────────────────────────
    image_files = sorted(img_dir.glob("*.*"))
    manifest_rows = []
    converted = 0
    skipped   = 0

    for img_path in image_files:
        lbl_path = label_dir / (img_path.stem + ".txt")
        out_lbl  = stage / "labels_converted" / (img_path.stem + ".txt")

        if lbl_path.exists():
            boxes = read_yolo_label(lbl_path)
            weapon_boxes = remap_classes(boxes, KEEP_CLASSES, REMAP)
        else:
            weapon_boxes = []
            log.warning(f"  Missing label for {img_path.name}, treating as negative")

        write_yolo_label(out_lbl, weapon_boxes)
        converted += 1

        manifest_rows.append({
            "image_path": str(img_path),
            "label_path": str(out_lbl),
            "split": TARGET_SPLIT,
            "dataset": DATASET_NAME,
            "is_negative": len(weapon_boxes) == 0,
        })

    append_manifest(manifest_rows)
    log.info(
        f"[{DATASET_NAME}] Done. "
        f"{converted} images → train | {skipped} skipped"
    )


if __name__ == "__main__":
    main()
