"""
converters/ds12_weapon_yolo.py

Dataset: Weapon_Detection_for_Yolo
S3 prefix: weapon_datasets/Weapon_Detection_for_Yolo/   (or root level)
Format: YOLO, 1 class (0=Weapon)
Splits: train/, val/, test/

Action: Direct copy — already correct format and class id.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_download_prefix, s3_list_objects,
    read_yolo_label, write_yolo_label, write_empty_label,
)

DATASET_NAME = "ds12_weapon_yolo"

S3_PREFIXES = [
    "weapon_datasets/Weapon_Detection_for_Yolo/",
    "Weapon_Detection_for_Yolo/",
]

SPLIT_MAP = {
    "train": "train",
    "val":   "val",
    "test":  "test",
}


def find_s3_prefix() -> str:
    for prefix in S3_PREFIXES:
        keys = s3_list_objects(prefix)
        if keys:
            return prefix
    raise RuntimeError(f"Cannot find {DATASET_NAME} in S3. Checked: {S3_PREFIXES}")


def process_split(s3_prefix, s3_split, our_split, stage) -> list:
    img_dir     = stage / s3_split / "images"
    lbl_dir     = stage / s3_split / "labels"
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
            raw = read_yolo_label(lbl_path)
            boxes = [(0, cx, cy, w, h) for cls, cx, cy, w, h in raw if cls == 0]
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
    log.info(f"[{DATASET_NAME}] Starting...")
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
