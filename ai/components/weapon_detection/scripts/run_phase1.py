#!/usr/bin/env python3
"""
run_phase1.py — Master runner for Phase 1: Dataset Unification

Runs all steps in the correct order.
Safe to interrupt and re-run — each converter is idempotent.

Usage:
    python run_phase1.py                    # run everything
    python run_phase1.py --skip-videos      # skip video extraction (faster for testing)
    python run_phase1.py --only ds1 ds5     # run only specific converters
    python run_phase1.py --from ds8         # start from a specific converter

Converters run in this order:
  ds1  → weapon_dataset1_cctv_weapon
  ds2  → normal_dataset2_umbrellas
  ds3  → normal_dataset3_virat (video, slow)
  ds5  → weapon_dataset5_ninja
  ds6  → weapon_dataset6_CCTV_Gun (UCF, requires manual video download)
  ds8  → weapon_dataset8_roboflow
  ds9  → weapon_dataset9_roboflow
  ds10 → weapon_dataset10_roboflow
  ds11 → HARIS_Weapon_Detection_Dataset
  ds12 → Weapon_Detection_for_Yolo
  ds13 → UCFDataset normal videos (video, slow)
  mall → normal_dataset1_mall frames
"""

import sys
import argparse
import importlib
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import log

# Ordered list of (id, module_path, description)
CONVERTERS = [
    ("ds1",  "data.parsers.ds1_cctv_weapon",  "CCTV Weapon (YOLO remap)"),
    ("ds2",  "data.parsers.ds2_umbrellas",    "Umbrellas hard negatives"),
    ("ds3",  "data.parsers.ds3_virat",        "VIRAT videos → negatives [SLOW]"),
    ("ds5",  "data.parsers.ds5_ninja",        "Ninja/Supervisely → YOLO"),
    ("ds6",  "data.parsers.ds6_ucf",          "CCTV-GUN UCF COCO → YOLO [NEEDS MANUAL DOWNLOAD]"),
    ("ds8",  "data.parsers.ds8_roboflow",     "Roboflow8 (Weapon, 1-class)"),
    ("ds9",  "data.parsers.ds9_roboflow",     "Roboflow9 (Gun, auto-split)"),
    ("ds10", "data.parsers.ds10_roboflow",    "Roboflow10 (2-class, weapon only)"),
    ("ds11", "data.parsers.ds11_haris",       "HARIS (gun+knife → weapon)"),
    ("ds12", "data.parsers.ds12_weapon_yolo", "Weapon_Detection_for_Yolo"),
    ("ds13", "data.parsers.ds13_ucf_normal",  "UCF normal videos → negatives [SLOW]"),
]


def run_step(label: str, fn, description: str) -> bool:
    log.info(f"\n{'─'*60}")
    log.info(f"  RUNNING: [{label}] {description}")
    log.info(f"{'─'*60}")
    t0 = time.time()
    try:
        fn()
        elapsed = time.time() - t0
        log.info(f"  ✓ [{label}] completed in {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - t0
        log.error(f"  ✗ [{label}] FAILED after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Phase 1 master runner")
    parser.add_argument("--skip-videos", action="store_true",
                        help="Skip ds3 (VIRAT) and ds13 (UCF normal) video extraction")
    parser.add_argument("--only", nargs="+", metavar="ID",
                        help="Run only these converter IDs (e.g. --only ds1 ds5)")
    parser.add_argument("--from", dest="from_id", metavar="ID",
                        help="Start from this converter ID (skip earlier ones)")
    parser.add_argument("--skip-merge", action="store_true",
                        help="Skip the final merge step")
    args = parser.parse_args()

    # ── Step 0: Create dirs ──────────────────────────────────────────────────
    from scripts.s00_create_dirs import main as create_dirs
    # Only reset if running from scratch
    if not args.from_id and not args.only:
        run_step("00", create_dirs, "Create directory structure")
    else:
        log.info("Skipping dir creation (partial run)")

    # ── Build list of converters to run ─────────────────────────────────────
    converters_to_run = CONVERTERS[:]

    if args.from_id:
        ids = [c[0] for c in CONVERTERS]
        if args.from_id not in ids:
            log.error(f"Unknown converter id: {args.from_id}. Valid: {ids}")
            sys.exit(1)
        start_idx = ids.index(args.from_id)
        converters_to_run = CONVERTERS[start_idx:]

    if args.only:
        converters_to_run = [c for c in converters_to_run if c[0] in args.only]
        if not converters_to_run:
            log.error(f"No converters matched --only {args.only}")
            sys.exit(1)

    if args.skip_videos:
        converters_to_run = [c for c in converters_to_run if c[0] not in ("ds3", "ds13")]
        log.info("Skipping video converters (ds3, ds13)")

    # ── Run converters ───────────────────────────────────────────────────────
    results = {}
    t_start = time.time()

    for conv_id, module_path, description in converters_to_run:
        try:
            mod = importlib.import_module(module_path)
            fn  = mod.main
        except ImportError as e:
            log.error(f"Cannot import {module_path}: {e}")
            results[conv_id] = False
            continue

        ok = run_step(conv_id, fn, description)
        results[conv_id] = ok

    # ── Merge ────────────────────────────────────────────────────────────────
    if not args.skip_merge:
        from scripts.s01_merge_splits import main as merge
        run_step("merge", merge, "Merge staging → final splits")

        from scripts.s02_validate_dataset import main as validate
        run_step("validate", validate, "Validate final dataset")

        from scripts.s03_stats import main as stats
        run_step("stats", stats, "Print statistics")

    # ── Summary ──────────────────────────────────────────────────────────────
    total_time = time.time() - t_start
    log.info(f"\n{'='*60}")
    log.info(f"  PHASE 1 COMPLETE — {total_time/60:.1f} minutes")
    log.info(f"{'='*60}")
    failed = [k for k, v in results.items() if not v]
    passed = [k for k, v in results.items() if v]
    log.info(f"  ✓ Passed: {passed}")
    if failed:
        log.warning(f"  ✗ Failed: {failed}")
        log.warning("  Re-run failed converters individually to debug.")
    else:
        log.info("  All converters succeeded.")


import scripts.s00_create_dirs  

if __name__ == "__main__":
    import importlib.util, types

    def patch_script(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod  = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)

    base = Path(__file__).parent
    patch_script("scripts.s00_create_dirs",    base / "scripts/00_create_dirs.py")
    patch_script("scripts.s01_merge_splits",   base / "scripts/01_merge_splits.py")
    patch_script("scripts.s02_validate_dataset", base / "scripts/02_validate_dataset.py")
    patch_script("scripts.s03_stats",          base / "scripts/03_stats.py")

    main()
