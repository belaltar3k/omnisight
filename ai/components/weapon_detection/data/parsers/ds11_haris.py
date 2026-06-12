"""
converters/ds11_haris.py

Dataset: HARIS_Weapon_Detection_Dataset
S3 prefix: weapon_datasets/HARIS_Weapon_Detection_Dataset/   (adjust if in different root)
           OR: HARIS_Weapon_Detection_Dataset/
Format: YOLO, 2 classes: 0=gun, 1=knife
Splits: train/, val/ (NO test)

Action:
  - Both class 0 (gun) and class 1 (knife) → remap to 0 (weapon)
  - train/ → train
  - val/   → val
  - This is a pre-merged, already cleaned dataset — high quality

NOTE: This dataset's images use prefix ds_1__, ds_3__, etc.
They overlap with ds1_cctv_weapon original images but are renamed.
Deduplication in phase 2 will handle any true duplicates.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_download_prefix,
    read_yolo_label, write_yolo_label, write_empty_label,
)

DATASET_NAME = "ds11_haris"

# Try both possible S3 locations
S3_PREFIXES = [
    "weapon_datasets/HARIS_Weapon_Detection_Dataset/",
    "HARIS_Weapon_Detection_Dataset/",
]

SPLIT_MAP = {
    "train": "train",
    "val":   "val",
}

# Both gun (0) and knife (1) → weapon (0)
REMAP = {0: 0, 1: 0}


def find_s3_prefix() -> str:
    """Try to find which S3 prefix this dataset is under."""
    from data.utils import s3_list_objects
    for prefix in S3_PREFIXES:
        keys = s3_list_objects(prefix)
        if keys:
            log.info(f"  Found at S3 prefix: {prefix}")
            return prefix
    raise RuntimeError(
        f"Could not find HARIS dataset under any of: {S3_PREFIXES}\n"
        "Check your S3 bucket structure and update S3_PREFIXES."
    )


def process_split(s3_prefix: str, s3_split: str, our_split: str, stage: Path) -> list:
    img_dir = stage / s3_split / "images"
    lbl_dir = stage / s3_split / "labels"
    out_lbl_dir = stage / s3_split / "labels_converted"

    s3_download_prefix(
        s3_prefix + s3_split + "/images/",
        img_dir,
        extensions=(".jpg", ".jpeg", ".png"),
        desc=f"{DATASET_NAME}/{s3_split} images",
    )
    s3_download_prefix(
        s3_prefix + s3_split + "/labels/",
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
            # Remap both gun and knife → weapon (0)
            boxes = [(REMAP.get(cls, 0), cx, cy, w, h) for cls, cx, cy, w, h in raw_boxes]
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
    log.info(f"[{DATASET_NAME}] Starting (gun + knife → weapon)...")
    stage = staging_dir(DATASET_NAME)

    try:
        s3_prefix = find_s3_prefix()
    except RuntimeError as e:
        log.error(str(e))
        return

    all_rows = []
    for s3_split, our_split in SPLIT_MAP.items():
        rows = process_split(s3_prefix, s3_split, our_split, stage)
        all_rows.extend(rows)

    append_manifest(all_rows)
    log.info(f"[{DATASET_NAME}] Done. {len(all_rows)} images.")


if __name__ == "__main__":
    main()
