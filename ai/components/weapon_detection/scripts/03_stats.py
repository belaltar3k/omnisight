"""
scripts/03_stats.py

Print final dataset statistics:
  - Per-split image counts
  - Per-dataset contribution
  - Positive/negative balance
  - Bbox size distribution (small / medium / large)
  - Estimated training time at typical GPU speeds
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import log, BASE_OUT, MANIFEST_CSV, SPLITS
from data.utils import read_yolo_label

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def bbox_category(w, h):
    """Categorize bbox by area (COCO convention scaled to [0,1])."""
    area = w * h
    if area < 0.002:    # < 32x32 in a 640px image
        return "small"
    elif area < 0.02:   # < 96x96
        return "medium"
    else:
        return "large"


def main():
    log.info("Computing dataset statistics...")
    print("\n" + "=" * 70)
    print("  UNIFIED WEAPON DATASET — STATISTICS")
    print("=" * 70)

    # ── Per-split counts from filesystem ────────────────────────────────────
    print("\n📁 SPLIT BREAKDOWN")
    print(f"  {'Split':<8} {'Images':>8} {'Positive':>10} {'Negative':>10} {'Pos%':>6}")
    print(f"  {'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*6}")

    grand_total = 0
    for split in SPLITS:
        img_dir = BASE_OUT / split / "images"
        lbl_dir = BASE_OUT / split / "labels"
        if not img_dir.exists():
            continue

        imgs = [f for f in img_dir.glob("*.*") if f.suffix.lower() in IMAGE_EXTS]
        n_pos = n_neg = 0
        bbox_sizes = defaultdict(int)
        total_boxes = 0

        for img in imgs:
            lbl = lbl_dir / (img.stem + ".txt")
            if lbl.exists():
                boxes = read_yolo_label(lbl)
                if boxes:
                    n_pos += 1
                    for _, cx, cy, w, h in boxes:
                        bbox_sizes[bbox_category(w, h)] += 1
                        total_boxes += 1
                else:
                    n_neg += 1
            else:
                n_neg += 1

        total = n_pos + n_neg
        grand_total += total
        pos_pct = (n_pos / total * 100) if total > 0 else 0
        print(f"  {split:<8} {total:>8,} {n_pos:>10,} {n_neg:>10,} {pos_pct:>5.1f}%")

        if total_boxes > 0:
            print(f"           Bboxes: {total_boxes:,} total | "
                  f"small={bbox_sizes['small']:,} "
                  f"medium={bbox_sizes['medium']:,} "
                  f"large={bbox_sizes['large']:,}")

    print(f"  {'TOTAL':<8} {grand_total:>8,}")

    # ── Per-dataset contribution (from manifest) ─────────────────────────────
    if MANIFEST_CSV.exists():
        print("\n📊 PER-DATASET CONTRIBUTION")
        print(f"  {'Dataset':<35} {'Train':>7} {'Val':>6} {'Test':>6} {'Total':>7} {'Neg%':>6}")
        print(f"  {'-'*35} {'-'*7} {'-'*6} {'-'*6} {'-'*7} {'-'*6}")

        ds_split_counts = defaultdict(lambda: defaultdict(int))
        ds_neg_counts   = defaultdict(int)

        with open(MANIFEST_CSV) as f:
            for row in csv.DictReader(f):
                ds = row["dataset"]
                sp = row["split"]
                ds_split_counts[ds][sp] += 1
                if row["is_negative"].lower() == "true":
                    ds_neg_counts[ds] += 1

        for ds in sorted(ds_split_counts.keys()):
            counts = ds_split_counts[ds]
            total  = sum(counts.values())
            neg    = ds_neg_counts[ds]
            neg_pct = (neg / total * 100) if total > 0 else 0
            print(
                f"  {ds:<35} "
                f"{counts.get('train',0):>7,} "
                f"{counts.get('val',0):>6,} "
                f"{counts.get('test',0):>6,} "
                f"{total:>7,} "
                f"{neg_pct:>5.1f}%"
            )

    # ── Training time estimate ───────────────────────────────────────────────
    train_dir = BASE_OUT / "train" / "images"
    if train_dir.exists():
        n_train = len([f for f in train_dir.glob("*.*") if f.suffix.lower() in IMAGE_EXTS])
        # YOLOv11x at 1280px on A100 80GB: ~0.8s/batch with batch=8
        # On 24GB (A10G/RTX 3090): ~1.2s/batch with batch=4
        batch_size   = 4
        secs_per_batch = 1.2
        epochs = 100
        batches_per_epoch = n_train / batch_size
        total_hours = (batches_per_epoch * secs_per_batch * epochs) / 3600

        print(f"\n⏱  ESTIMATED TRAINING TIME (YOLOv11x, 1280px, 24GB VRAM)")
        print(f"   Batch size: {batch_size} | ~{secs_per_batch}s/batch")
        print(f"   {n_train:,} train images × {epochs} epochs = {total_hours:.0f}h")
        print(f"   (Use --batch 8 or 16 with AMP for faster training)")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
