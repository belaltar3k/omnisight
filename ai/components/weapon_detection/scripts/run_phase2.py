"""
phase2/run_phase2.py

Phase 2: Deduplication + Balance

Steps:
  1. Perceptual hash deduplication (pHash + BK-tree)
  2. Positive/negative balance check and trim
  3. Final stats
  4. Write phase2 report

Usage:
    python phase2/run_phase2.py
    python phase2/run_phase2.py --dry-run          # preview only, no deletions
    python phase2/run_phase2.py --threshold 6      # stricter dedup (default 8)
    python phase2/run_phase2.py --neg-ratio 0.35   # target 35% negatives (default 40%)
    python phase2/run_phase2.py --skip-dedup       # skip dedup, only balance
    python phase2/run_phase2.py --skip-balance     # skip balance, only dedup
"""

import sys
import time
import argparse
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import log, BASE_OUT, SPLITS

REPORT_PATH = BASE_OUT / "phase2_report.json"


def count_images(split: str) -> int:
    img_dir = BASE_OUT / split / "images"
    if not img_dir.exists():
        return 0
    return len([f for f in img_dir.glob("*.*")
                if f.suffix.lower() in {".jpg", ".jpeg", ".png"}])


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Dedup + Balance")
    parser.add_argument("--dry-run",      action="store_true",
                        help="Preview only — no files deleted")
    parser.add_argument("--threshold",    type=int, default=8,
                        help="Hamming distance threshold for dedup (default: 8)")
    parser.add_argument("--neg-ratio",    type=float, default=0.40,
                        help="Target negative ratio in train (default: 0.40)")
    parser.add_argument("--skip-dedup",   action="store_true")
    parser.add_argument("--skip-balance", action="store_true")
    args = parser.parse_args()

    t0 = time.time()
    report = {
        "timestamp":  datetime.now().isoformat(),
        "dry_run":    args.dry_run,
        "threshold":  args.threshold,
        "neg_ratio":  args.neg_ratio,
        "before": {},
        "dedup_stats": {},
        "balance_stats": {},
        "after": {},
    }

    # ── Before snapshot ──────────────────────────────────────────────────────
    log.info("\n" + "="*60)
    log.info("  PHASE 2 — DEDUPLICATION & BALANCE")
    log.info("="*60)
    log.info("\nBefore counts:")
    for split in SPLITS:
        n = count_images(split)
        report["before"][split] = n
        log.info(f"  {split}: {n:,} images")

    # ── Step 1: Deduplication ────────────────────────────────────────────────
    if not args.skip_dedup:
        log.info("\n── STEP 1: Perceptual Deduplication ──")
        from data.dedup import run_deduplication, THRESHOLD
        import data.dedup as dedup_mod
        dedup_mod.THRESHOLD = args.threshold   # allow CLI override

        dedup_stats = run_deduplication(dry_run=args.dry_run)
        report["dedup_stats"] = dedup_stats

        log.info("\nDedup summary:")
        log.info(f"  Total images scanned:  {dedup_stats['total_images']:,}")
        log.info(f"  Duplicate pairs found: {dedup_stats['duplicate_pairs']:,}")
        log.info(f"  Clusters:              {dedup_stats['dup_clusters']:,}")
        log.info(f"  Deleted:               {dedup_stats['deleted']:,} ({dedup_stats['dup_rate_pct']}%)")
        log.info(f"  Remaining:             {dedup_stats['remaining']:,}")
    else:
        log.info("\n── STEP 1: Deduplication SKIPPED ──")

    # ── Step 2: Balance ──────────────────────────────────────────────────────
    if not args.skip_balance:
        log.info("\n── STEP 2: Positive/Negative Balance ──")
        from data.balance import run_balance
        balance_stats = run_balance(dry_run=args.dry_run, target_neg_ratio=args.neg_ratio)
        report["balance_stats"] = balance_stats
    else:
        log.info("\n── STEP 2: Balance SKIPPED ──")

    # ── After snapshot ───────────────────────────────────────────────────────
    log.info("\nAfter counts:")
    for split in SPLITS:
        n = count_images(split)
        report["after"][split] = n
        before = report["before"].get(split, 0)
        delta  = n - before
        log.info(f"  {split}: {n:,} images  (Δ {delta:+,})")

    # ── Write report ─────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    report["elapsed_seconds"] = round(elapsed, 1)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    log.info(f"\nPhase 2 report saved: {REPORT_PATH}")

    log.info(f"\n{'='*60}")
    log.info(f"  PHASE 2 COMPLETE — {elapsed/60:.1f} minutes")
    if args.dry_run:
        log.info("  [DRY RUN] No files were modified.")
    log.info("="*60)
    log.info("\nNext: run Phase 3 training (phase3/run_phase3.py)")


if __name__ == "__main__":
    main()
