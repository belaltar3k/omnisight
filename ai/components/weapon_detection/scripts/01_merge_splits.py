"""
scripts/01_merge_splits.py

Read the manifest CSV and copy all files into the final unified structure:
  /data/datasets/unified/train/images/
  /data/datasets/unified/train/labels/
  /data/datasets/unified/val/images/
  /data/datasets/unified/val/labels/
  /data/datasets/unified/test/images/
  /data/datasets/unified/test/labels/

Rules:
  1. Filename conflicts: prefix with dataset name to guarantee uniqueness.
  2. Verify every image has a corresponding label (create empty if missing).
  3. Skip images that failed to download (path doesn't exist).
  4. Log per-split counts.
"""

import sys
import csv
import shutil
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import (
    log, BASE_OUT, MANIFEST_CSV, SPLITS,
    write_empty_label,
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}


def safe_dst_name(dataset: str, img_path: Path) -> str:
    """
    Build a collision-safe filename:
      <dataset>__<original_stem><suffix>
    """
    return f"{dataset}__{img_path.stem}{img_path.suffix.lower()}"


def main():
    if not MANIFEST_CSV.exists():
        log.error(f"Manifest not found: {MANIFEST_CSV}")
        log.error("Run all converters first.")
        sys.exit(1)

    log.info("Reading manifest...")
    rows = []
    with open(MANIFEST_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    log.info(f"  {len(rows)} entries in manifest")

    split_stem_counts = defaultdict(lambda: defaultdict(int))
    for row in rows:
        stem = Path(row["image_path"]).stem
        split_stem_counts[row["split"]][stem] += 1

    stats = defaultdict(lambda: {"pos": 0, "neg": 0, "skipped": 0})

    log.info("Copying files to final split directories...")

    for row in tqdm(rows, desc="Merging", unit="file"):
        img_src  = Path(row["image_path"])
        lbl_src  = Path(row["label_path"])
        split    = row["split"]
        dataset  = row["dataset"]
        is_neg   = row["is_negative"].lower() == "true"

        if split not in SPLITS:
            log.warning(f"  Unknown split '{split}' for {img_src.name}, skipping")
            stats[split]["skipped"] += 1
            continue

        if not img_src.exists():
            log.debug(f"  Image not found, skipping: {img_src}")
            stats[split]["skipped"] += 1
            continue

        # Build destination filename
        stem = img_src.stem
        if split_stem_counts[split][stem] > 1:
            # Collision → prefix with dataset name
            dst_name = safe_dst_name(dataset, img_src)
        else:
            dst_name = img_src.stem + img_src.suffix.lower()

        dst_img = BASE_OUT / split / "images" / dst_name
        dst_lbl = BASE_OUT / split / "labels" / (Path(dst_name).stem + ".txt")

        # Copy image
        if not dst_img.exists():
            shutil.copy2(img_src, dst_img)

        # Copy or create label
        if lbl_src.exists():
            if not dst_lbl.exists():
                shutil.copy2(lbl_src, dst_lbl)
        else:
            # Label missing — create empty (treat as negative)
            log.debug(f"  Label missing for {img_src.name}, creating empty")
            write_empty_label(dst_lbl)
            is_neg = True

        if is_neg:
            stats[split]["neg"] += 1
        else:
            stats[split]["pos"] += 1

    # Final summary
    log.info("\n" + "=" * 60)
    log.info("MERGE COMPLETE — Final counts:")
    total_images = 0
    for split in SPLITS:
        s = stats[split]
        total = s["pos"] + s["neg"]
        total_images += total
        neg_pct = (s["neg"] / total * 100) if total > 0 else 0
        log.info(
            f"  {split:5s}: {total:6d} images | "
            f"{s['pos']:6d} positive | "
            f"{s['neg']:6d} negative ({neg_pct:.1f}%) | "
            f"{s['skipped']:4d} skipped"
        )
    log.info(f"  TOTAL: {total_images} images")
    log.info("=" * 60)

    # Verify image ↔ label pairing
    log.info("\nVerifying image–label pairing...")
    mismatches = 0
    for split in SPLITS:
        img_dir = BASE_OUT / split / "images"
        lbl_dir = BASE_OUT / split / "labels"
        for img_path in img_dir.glob("*.*"):
            lbl_path = lbl_dir / (img_path.stem + ".txt")
            if not lbl_path.exists():
                log.warning(f"  Missing label: {lbl_path}")
                write_empty_label(lbl_path)
                mismatches += 1
    if mismatches:
        log.warning(f"  Fixed {mismatches} missing labels (created empty files)")
    else:
        log.info("  All images have matching labels ✓")


if __name__ == "__main__":
    main()
