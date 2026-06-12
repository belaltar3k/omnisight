"""
converters/ds6_ucf.py

Dataset: weapon_dataset6_CCTV_Gun — UCF subset ONLY
S3 prefix: weapon_datasets/weapon_dataset6_CCTV_Gun/data/ucf/

Structure:
  annotation_detection/
    annotations_all.json    ← COCO format
    annotations_train.json
    annotations_val.json
    annotations_test.json
  frames.json               ← maps {video_name: [[global_id, frame_number], ...]}
  images/                   ← NOT in S3 — must be extracted from UCF Crime videos

The images must be extracted from Anomaly-Videos-Part-3.zip which the user
downloads separately. This script assumes frames are already extracted into:
  /data/raw/ucf_crime/Anomaly-Videos-Part-3/<VideoName>/

frames.json tells us exactly which frame numbers to extract per video.
annotations_*.json tells us which image IDs map to bounding boxes.

COCO annotation structure:
  images: [{id, file_name, width, height}]
  annotations: [{image_id, bbox:[x,y,w,h], category_id}]
  categories: [{id, name}]  ← category 1 = handgun

Action:
  - Extract required frames from UCF Crime videos using ffmpeg
  - Convert COCO bboxes to YOLO format
  - Use train/val/test splits from annotations_*.json
  - This is the HELD-OUT test set → highest quality real CCTV

WARNING: The test split from this dataset must NEVER be in training.
"""

import sys
import json
import shutil
import subprocess
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_download_prefix, s3_read_json, s3_download,
    write_yolo_label, write_empty_label,
    coco_to_yolo,
    BUCKET,
)

DATASET_NAME = "ds6_ucf"
S3_ANN_PREFIX = "weapon_datasets/weapon_dataset6_CCTV_Gun/data/ucf/annotation_detection/"
S3_FRAMES_JSON = "weapon_datasets/weapon_dataset6_CCTV_Gun/data/ucf/frames.json"

# Where user extracted Anomaly-Videos-Part-3.zip
UCF_VIDEOS_ROOT = Path("/data/raw/ucf_crime/Anomaly-Videos-Part-3")

# Map annotation split files to our dataset splits
SPLIT_FILES = {
    "annotations_train.json": "train",
    "annotations_val.json":   "val",
    "annotations_test.json":  "test",
}

# COCO category id for handgun/weapon (check your annotations_all.json)
# Typically category_id=1 in CCTV-GUN annotations
WEAPON_CATEGORY_IDS = {1}  # adjust if needed after inspecting annotations_all.json


def extract_frame(video_path: Path, frame_number: int, out_path: Path) -> bool:
    """Extract a specific frame number from a video using ffmpeg."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"select=eq(n\\,{frame_number})",
        "-vframes", "1",
        "-q:v", "2",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0 and out_path.exists()


def find_video_file(video_name: str) -> Path | None:
    """
    UCF Crime videos are organized as:
      Anomaly-Videos-Part-3/<CategoryName>/<VideoName>/<VideoName>.avi
    or various other extensions. Search recursively.
    """
    if not UCF_VIDEOS_ROOT.exists():
        return None
    # Try common extensions
    for ext in (".avi", ".mp4", ".mpg", ".mov"):
        matches = list(UCF_VIDEOS_ROOT.rglob(f"{video_name}{ext}"))
        if matches:
            return matches[0]
    return None


def load_coco_annotations(ann_data: dict) -> tuple:
    """
    Parse COCO annotation dict.
    Returns:
      id_to_image: {image_id: {file_name, width, height}}
      id_to_boxes: {image_id: [(cx, cy, w, h), ...]}  normalized YOLO coords
    """
    id_to_image = {}
    for img in ann_data.get("images", []):
        id_to_image[img["id"]] = img

    id_to_boxes = defaultdict(list)
    for ann in ann_data.get("annotations", []):
        if ann.get("category_id") not in WEAPON_CATEGORY_IDS:
            continue
        img_info = id_to_image.get(ann["image_id"])
        if not img_info:
            continue
        W, H = img_info["width"], img_info["height"]
        cx, cy, nw, nh = coco_to_yolo(ann["bbox"], W, H)
        id_to_boxes[ann["image_id"]].append((0, cx, cy, nw, nh))

    return id_to_image, id_to_boxes


def main():
    log.info(f"[{DATASET_NAME}] Starting COCO → YOLO conversion (UCF Crime)...")

    if not UCF_VIDEOS_ROOT.exists():
        log.warning(
            f"UCF Crime videos not found at {UCF_VIDEOS_ROOT}\n"
            "  Please download Anomaly-Videos-Part-3.zip from:\n"
            "  https://www.dropbox.com/sh/75v5ehq4cdg5g5g/AABvnJSwZI7zXb8_myBA0CLHa\n"
            "  and extract to /data/raw/ucf_crime/\n"
            "  Then re-run this script.\n"
            "  Skipping ds6_ucf for now."
        )
        return

    stage = staging_dir(DATASET_NAME)
    ann_dir = stage / "annotations"
    ann_dir.mkdir(parents=True, exist_ok=True)

    # Download annotation files
    s3_download_prefix(S3_ANN_PREFIX, ann_dir, extensions=(".json",),
                       desc=f"{DATASET_NAME} annotations")

    # Load frames.json to know which frame# corresponds to each image file
    log.info("  Loading frames.json...")
    frames_json = s3_read_json(S3_FRAMES_JSON)
    # frames_json: {video_name: [[global_id, frame_number], ...]}
    # global_id maps to image file names in annotations (e.g., "1335.jpg" → id 1335)
    # Build: {global_id (int): (video_name, frame_number)}
    global_id_to_frame = {}
    for video_name, frame_list in frames_json.items():
        seen = set()
        for entry in frame_list:
            gid, frame_num = entry[0], entry[1]
            gid = int(gid)
            frame_num = int(frame_num)
            if gid not in seen:  # frames.json has duplicates (str + int keys)
                global_id_to_frame[gid] = (video_name, frame_num)
                seen.add(gid)

    log.info(f"  frames.json: {len(global_id_to_frame)} unique frame mappings")

    all_manifest_rows = []

    for ann_filename, split in SPLIT_FILES.items():
        ann_path = ann_dir / ann_filename
        if not ann_path.exists():
            log.warning(f"  Missing {ann_filename}, skipping {split} split")
            continue

        log.info(f"  Processing {ann_filename} → {split}...")
        ann_data = json.loads(ann_path.read_text())
        id_to_image, id_to_boxes = load_coco_annotations(ann_data)

        out_img_dir = stage / "images" / split
        out_lbl_dir = stage / "labels" / split
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        n_ok = n_missing_video = n_frame_fail = 0

        for img_id, img_info in id_to_image.items():
            # image id IS the global frame id in frames.json
            frame_info = global_id_to_frame.get(img_id)
            if frame_info is None:
                log.debug(f"    No frame mapping for image_id={img_id}, skipping")
                n_missing_video += 1
                continue

            video_name, frame_number = frame_info
            video_path = find_video_file(video_name)
            if video_path is None:
                log.debug(f"    Video not found: {video_name}")
                n_missing_video += 1
                continue

            # Output paths
            out_stem = f"ds6_ucf_{img_id}"
            out_img  = out_img_dir / f"{out_stem}.jpg"
            out_lbl  = out_lbl_dir / f"{out_stem}.txt"

            # Extract frame
            if not out_img.exists():
                ok = extract_frame(video_path, frame_number, out_img)
                if not ok:
                    log.warning(f"    Frame extraction failed: {video_name} frame {frame_number}")
                    n_frame_fail += 1
                    continue

            # Write label
            boxes = id_to_boxes.get(img_id, [])
            if boxes:
                write_yolo_label(out_lbl, boxes)
                is_neg = False
            else:
                write_empty_label(out_lbl)
                is_neg = True

            all_manifest_rows.append({
                "image_path": str(out_img),
                "label_path": str(out_lbl),
                "split": split,
                "dataset": DATASET_NAME,
                "is_negative": is_neg,
            })
            n_ok += 1

        log.info(
            f"    {split}: {n_ok} ok | "
            f"{n_missing_video} missing video | "
            f"{n_frame_fail} frame extraction failures"
        )

    append_manifest(all_manifest_rows)
    log.info(
        f"[{DATASET_NAME}] Done. "
        f"{len(all_manifest_rows)} total frames registered."
    )


if __name__ == "__main__":
    main()
