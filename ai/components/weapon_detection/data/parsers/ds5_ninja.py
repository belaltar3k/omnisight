"""
converters/ds5_ninja.py

Dataset: weapon_dataset5_ninja (Supervisely format)
S3 prefix: weapon_datasets/weapon_dataset5_ninja/weapons-in-images/
Structure:
  train-weapons_in_images/
    img/   *.jpg
    ann/   *.jpg.json   ← Supervisely annotation format
  test-cctv/
    img/   *.jpg
    ann/   *.jpg.json

Annotation format:
  {
    "size": {"height": H, "width": W},
    "objects": [
      {
        "classTitle": "weapon",
        "geometryType": "rectangle",
        "points": {"exterior": [[x1,y1],[x2,y2]], "interior": []}
      }, ...
    ]
  }

Action:
  - Convert Supervisely rectangle → YOLO bbox, class 0
  - train-weapons_in_images → train split
  - test-cctv → test split  ← held-out CCTV domain
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_download_prefix, s3_list_objects, s3_read_json,
    write_yolo_label, write_empty_label,
    supervisely_rect_to_yolo,
    BUCKET,
)

DATASET_NAME = "ds5_ninja"
S3_PREFIX    = "weapon_datasets/weapon_dataset5_ninja/weapons-in-images/"

SUBSETS = {
    "train-weapons_in_images": "train",
    "test-cctv":               "test",
}


def convert_supervisely_ann(ann: dict) -> list:
    """Convert one Supervisely annotation dict to YOLO boxes."""
    W = ann["size"]["width"]
    H = ann["size"]["height"]
    boxes = []
    for obj in ann.get("objects", []):
        if obj.get("geometryType") != "rectangle":
            continue
        exterior = obj["points"]["exterior"]
        if len(exterior) < 2:
            continue
        cx, cy, w, h = supervisely_rect_to_yolo(exterior, W, H)
        if w > 0 and h > 0:
            boxes.append((0, cx, cy, w, h))
    return boxes


def process_subset(subset_name: str, split: str, stage: Path) -> list:
    """Download and convert one subset. Returns manifest rows."""
    s3_img_prefix = S3_PREFIX + subset_name + "/img/"
    s3_ann_prefix = S3_PREFIX + subset_name + "/ann/"

    img_dir = stage / subset_name / "img"
    ann_dir = stage / subset_name / "ann"
    out_img_dir = stage / "images" / split
    out_lbl_dir = stage / "labels" / split

    # Download images
    s3_download_prefix(
        s3_img_prefix, img_dir,
        extensions=(".jpg", ".jpeg", ".png"),
        desc=f"{DATASET_NAME}/{subset_name} images",
    )

    # Download annotations
    s3_download_prefix(
        s3_ann_prefix, ann_dir,
        extensions=(".json",),
        desc=f"{DATASET_NAME}/{subset_name} annotations",
    )

    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    image_files = sorted(img_dir.glob("*.*"))
    n_pos = n_neg = 0

    for img_path in image_files:
        # Supervisely ann file is named <image_filename>.json
        ann_path = ann_dir / (img_path.name + ".json")

        # Build unique output name: ds5_<subset>_<stem>
        out_stem = f"ds5_{subset_name}_{img_path.stem}"
        out_img  = out_img_dir / (out_stem + img_path.suffix)
        out_lbl  = out_lbl_dir / (out_stem + ".txt")

        # Copy image
        import shutil
        shutil.copy2(img_path, out_img)

        # Convert annotation
        if ann_path.exists():
            try:
                ann = json.loads(ann_path.read_text())
                boxes = convert_supervisely_ann(ann)
            except Exception as e:
                log.warning(f"  Failed to parse {ann_path.name}: {e}")
                boxes = []
        else:
            log.warning(f"  No annotation for {img_path.name}")
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
            "image_path": str(out_img),
            "label_path": str(out_lbl),
            "split": split,
            "dataset": DATASET_NAME,
            "is_negative": is_neg,
        })

    log.info(
        f"  {subset_name} → {split}: "
        f"{n_pos} positive, {n_neg} negative"
    )
    return manifest_rows


def main():
    log.info(f"[{DATASET_NAME}] Starting Supervisely → YOLO conversion...")
    stage = staging_dir(DATASET_NAME)
    all_rows = []

    for subset_name, split in SUBSETS.items():
        rows = process_subset(subset_name, split, stage)
        all_rows.extend(rows)

    append_manifest(all_rows)
    log.info(f"[{DATASET_NAME}] Done. {len(all_rows)} total images registered.")


if __name__ == "__main__":
    main()
