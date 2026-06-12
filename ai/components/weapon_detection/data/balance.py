"""
phase2/balance.py

After deduplication, check and fix the positive/negative ratio in train split.

Target: 60% positive / 40% negative (adjustable)

Strategy:
  - If negatives > target_neg_ratio: randomly drop excess negatives
  - If positives are too few vs negatives: warn but don't duplicate
    (duplication is done via augmentation during training, not on disk)
  - Never touch val or test splits
  - Write a balance report
"""

import sys
import random
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import log, BASE_OUT, SPLITS, read_yolo_label

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Target negative fraction in train (0.0–1.0)
# 0.40 = 40% negatives, 60% positives
TARGET_NEG_RATIO = 0.40

# Random seed for reproducibility
SEED = 42


def get_split_stats(split: str) -> dict:
    """Compute positive/negative counts for a split."""
    img_dir = BASE_OUT / split / "images"
    lbl_dir = BASE_OUT / split / "labels"

    positives = []
    negatives = []

    if not img_dir.exists():
        return {"positives": [], "negatives": [], "total": 0}

    for img_path in img_dir.glob("*.*"):
        if img_path.suffix.lower() not in IMAGE_EXTS:
            continue
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        if lbl_path.exists() and lbl_path.read_text().strip():
            positives.append(img_path)
        else:
            negatives.append(img_path)

    return {
        "positives": positives,
        "negatives": negatives,
        "total": len(positives) + len(negatives),
    }


def print_balance_report(stats_before: dict, stats_after: dict):
    print("\n" + "=" * 65)
    print("  DATASET BALANCE REPORT")
    print("=" * 65)
    print(f"\n  {'Split':<8} {'Before':>10} {'After':>10} {'Neg% Before':>12} {'Neg% After':>11}")
    print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*12} {'-'*11}")
    for split in SPLITS:
        b = stats_before.get(split, {})
        a = stats_after.get(split, {})
        b_total = b.get("total", 0)
        a_total = a.get("total", 0)
        b_neg   = len(b.get("negatives", []))
        a_neg   = len(a.get("negatives", []))
        b_pct   = (b_neg / b_total * 100) if b_total > 0 else 0
        a_pct   = (a_neg / a_total * 100) if a_total > 0 else 0
        print(f"  {split:<8} {b_total:>10,} {a_total:>10,} {b_pct:>11.1f}% {a_pct:>10.1f}%")
    print()


def run_balance(dry_run: bool = False, target_neg_ratio: float = TARGET_NEG_RATIO) -> dict:
    """
    Balance train split negative/positive ratio.
    Only operates on train — val and test are never touched.
    Returns stats dict.
    """
    log.info(f"Checking dataset balance (target neg ratio = {target_neg_ratio:.0%})...")

    stats_before = {}
    for split in SPLITS:
        stats_before[split] = get_split_stats(split)
        s = stats_before[split]
        neg_pct = (len(s["negatives"]) / s["total"] * 100) if s["total"] > 0 else 0
        log.info(
            f"  {split}: {s['total']:,} total | "
            f"{len(s['positives']):,} pos | "
            f"{len(s['negatives']):,} neg ({neg_pct:.1f}%)"
        )

    # ── Only balance train ───────────────────────────────────────────────────
    train_stats = stats_before["train"]
    n_pos = len(train_stats["positives"])
    n_neg = len(train_stats["negatives"])
    total = n_pos + n_neg

    if total == 0:
        log.warning("Train split is empty!")
        return {}

    current_neg_ratio = n_neg / total
    target_neg_count  = int(n_pos * target_neg_ratio / (1 - target_neg_ratio))

    n_removed = 0

    if current_neg_ratio > target_neg_ratio + 0.02:  # 2% tolerance band
        excess = n_neg - target_neg_count
        log.info(
            f"  Train negatives: {n_neg:,} ({current_neg_ratio:.1%}) "
            f"→ target: {target_neg_count:,} ({target_neg_ratio:.1%}) "
            f"→ removing {excess:,} excess negatives"
        )

        if excess > 0:
            random.seed(SEED)
            to_remove = random.sample(train_stats["negatives"], excess)

            if not dry_run:
                for img_path in tqdm(to_remove, desc="Removing excess negatives"):
                    lbl_path = BASE_OUT / "train" / "labels" / (img_path.stem + ".txt")
                    if img_path.exists():
                        img_path.unlink()
                    if lbl_path.exists():
                        lbl_path.unlink()
                    n_removed += 1
            else:
                log.info(f"  [DRY RUN] Would remove {excess} negatives")
                n_removed = excess

    elif current_neg_ratio < target_neg_ratio - 0.05:  # 5% lower tolerance
        shortfall = target_neg_count - n_neg
        log.warning(
            f"  Train negatives below target: {n_neg:,} ({current_neg_ratio:.1%}) "
            f"vs target {target_neg_ratio:.1%}. "
            f"Shortfall: {shortfall:,}.\n"
            f"  → Consider adding more negative video frames (re-run ds3_virat / ds13_ucf_normal "
            f"with lower FRAME_INTERVAL) or reducing FRAME_INTERVAL_SEC."
        )
    else:
        log.info(f"  Train balance is within tolerance ({current_neg_ratio:.1%} neg). No action needed.")

    # ── Final stats ──────────────────────────────────────────────────────────
    stats_after = {}
    for split in SPLITS:
        stats_after[split] = get_split_stats(split)

    print_balance_report(stats_before, stats_after)

    return {
        "negatives_removed": n_removed,
        "train_before": total,
        "train_after":  total - n_removed,
    }
