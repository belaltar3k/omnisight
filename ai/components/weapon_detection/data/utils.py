"""
utils/common.py
Shared helpers for all dataset converters.
"""

import os
import json
import shutil
import hashlib
import csv
import logging
from pathlib import Path
from typing import List, Tuple, Optional

import boto3
from botocore.exceptions import ClientError
from tqdm import tqdm

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")

# ── Paths ─────────────────────────────────────────────────────────────────────
BUCKET        = os.environ.get("S3_BUCKET", "omnisharp-fcds")
BASE_OUT      = Path(os.environ.get("DATASET_ROOT", "/data/datasets/unified"))
STAGING       = BASE_OUT / "staging"
MANIFEST_CSV  = BASE_OUT / "manifest.csv"

SPLITS = ("train", "val", "test")


# ── S3 helpers ────────────────────────────────────────────────────────────────

def get_s3():
    return boto3.client("s3")


def s3_list_objects(prefix: str, suffix_filter: str = "") -> List[str]:
    """Return all object keys under prefix (handles pagination)."""
    s3 = get_s3()
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            k = obj["Key"]
            if suffix_filter and not k.lower().endswith(suffix_filter.lower()):
                continue
            keys.append(k)
    return keys


def s3_download(key: str, local_path: Path, overwrite: bool = False) -> bool:
    """Download a single S3 object. Returns True if downloaded."""
    if local_path.exists() and not overwrite:
        return False
    local_path.parent.mkdir(parents=True, exist_ok=True)
    s3 = get_s3()
    try:
        s3.download_file(BUCKET, key, str(local_path))
        return True
    except ClientError as e:
        log.error(f"Failed to download s3://{BUCKET}/{key}: {e}")
        return False


def s3_download_prefix(
    s3_prefix: str,
    local_dir: Path,
    extensions: Tuple[str, ...] = (),
    overwrite: bool = False,
    desc: str = "",
) -> List[Path]:
    """
    Download all objects under s3_prefix into local_dir,
    preserving relative structure. Returns list of downloaded local paths.
    """
    keys = s3_list_objects(s3_prefix)
    if extensions:
        keys = [k for k in keys if Path(k).suffix.lower() in extensions]

    local_paths = []
    for key in tqdm(keys, desc=desc or f"Downloading {s3_prefix}", unit="file"):
        rel = key[len(s3_prefix):]          # strip prefix
        local_path = local_dir / rel
        s3_download(key, local_path, overwrite=overwrite)
        local_paths.append(local_path)
    return local_paths


def s3_read_json(key: str) -> dict:
    """Download and parse a JSON file from S3 without saving to disk."""
    s3 = get_s3()
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return json.loads(obj["Body"].read().decode("utf-8"))


def s3_read_text(key: str) -> str:
    """Download and return text content of an S3 object."""
    s3 = get_s3()
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return obj["Body"].read().decode("utf-8", errors="replace")


# ── YOLO label helpers ────────────────────────────────────────────────────────

def write_yolo_label(label_path: Path, boxes: List[Tuple]) -> None:
    """
    Write YOLO format label file.
    boxes: list of (class_id, cx, cy, w, h) — all normalized [0,1]
    Empty list → empty file (negative sample).
    """
    label_path.parent.mkdir(parents=True, exist_ok=True)
    with open(label_path, "w") as f:
        for box in boxes:
            cls, cx, cy, w, h = box
            # Clamp to [0,1]
            cx = max(0.0, min(1.0, cx))
            cy = max(0.0, min(1.0, cy))
            w  = max(0.0, min(1.0, w))
            h  = max(0.0, min(1.0, h))
            if w > 0 and h > 0:
                f.write(f"{int(cls)} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")


def read_yolo_label(label_path: Path) -> List[Tuple]:
    """Read YOLO label file. Returns list of (cls, cx, cy, w, h)."""
    if not label_path.exists():
        return []
    boxes = []
    with open(label_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue  # skip malformed (e.g. OBB / polygon lines)
            try:
                cls = int(parts[0])
                cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                boxes.append((cls, cx, cy, w, h))
            except ValueError:
                continue
    return boxes


def remap_classes(
    boxes: List[Tuple],
    keep_classes: List[int],
    remap: dict,
) -> List[Tuple]:
    """
    Filter boxes to keep_classes and remap class ids.
    remap: {old_id: new_id}
    keep_classes: original class ids to retain
    """
    out = []
    for cls, cx, cy, w, h in boxes:
        if cls not in keep_classes:
            continue
        new_cls = remap.get(cls, cls)
        out.append((new_cls, cx, cy, w, h))
    return out


def coco_to_yolo(bbox, img_w, img_h):
    """
    Convert COCO bbox [x, y, width, height] (absolute) to
    YOLO [cx, cy, w, h] (normalized).
    """
    x, y, w, h = bbox
    cx = (x + w / 2) / img_w
    cy = (y + h / 2) / img_h
    nw = w / img_w
    nh = h / img_h
    return cx, cy, nw, nh


def supervisely_rect_to_yolo(exterior, img_w, img_h):
    """
    Convert Supervisely rectangle exterior [[x1,y1],[x2,y2]] to
    YOLO [cx, cy, w, h] normalized.
    """
    (x1, y1), (x2, y2) = exterior[0], exterior[1]
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    cx = (x1 + x2) / 2 / img_w
    cy = (y1 + y2) / 2 / img_h
    w  = (x2 - x1) / img_w
    h  = (y2 - y1) / img_h
    return cx, cy, w, h


# ── Image helpers ─────────────────────────────────────────────────────────────

def get_image_size(img_path: Path):
    """Return (width, height) without loading full image."""
    from PIL import Image
    with Image.open(img_path) as im:
        return im.size  # (width, height)


def is_valid_image(path: Path) -> bool:
    """Quick check that a file is a readable image."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def image_stem(path: Path) -> str:
    """Return filename without extension."""
    return path.stem


# ── Staging helpers ───────────────────────────────────────────────────────────

def staging_dir(dataset_name: str) -> Path:
    d = STAGING / dataset_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_empty_label(label_path: Path) -> None:
    """Write an empty label file (negative sample)."""
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.touch()


# ── Manifest ──────────────────────────────────────────────────────────────────

def append_manifest(rows: List[dict]) -> None:
    """
    Append rows to the manifest CSV.
    Each row: {image_path, label_path, split, dataset, is_negative}
    """
    MANIFEST_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_header = not MANIFEST_CSV.exists()
    with open(MANIFEST_CSV, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["image_path", "label_path", "split", "dataset", "is_negative"],
        )
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
