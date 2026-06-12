"""
run_all.py — Top-level entry point for the ENTIRE pipeline (Phase 1 + 2 + 3)

Usage:
    python run_all.py                      # full pipeline
    python run_all.py --phase 2            # only phase 2
    python run_all.py --phase 3            # only phase 3
    python run_all.py --phase 3 --config-only  # generate configs only
"""

import sys
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import log, BASE_OUT


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     WEAPON DETECTION — FULL TRAINING PIPELINE               ║
║     Phase 1: Dataset Unification                            ║
║     Phase 2: Deduplication + Balance                        ║
║     Phase 3: Training + Evaluation                          ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(description="Full weapon detection pipeline")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], default=None,
                        help="Run only a specific phase (default: all)")
    parser.add_argument("--skip-videos",    action="store_true",
                        help="[Phase 1] Skip video extraction (VIRAT + UCF normal)")
    parser.add_argument("--dry-run",        action="store_true",
                        help="[Phase 2] Preview dedup/balance without deleting")
    parser.add_argument("--threshold",      type=int, default=8,
                        help="[Phase 2] pHash Hamming threshold (default: 8)")
    parser.add_argument("--neg-ratio",      type=float, default=0.40,
                        help="[Phase 2] Target negative ratio (default: 0.40)")
    parser.add_argument("--config-only",    action="store_true",
                        help="[Phase 3] Only write config files")
    parser.add_argument("--eval-only",      action="store_true",
                        help="[Phase 3] Only run evaluation")
    args = parser.parse_args()

    print_banner()
    t_global = time.time()
    run_phase = args.phase

    # ── Phase 1 ──────────────────────────────────────────────────────────────
    if run_phase in (None, 1):
        log.info("╔══ PHASE 1: Dataset Unification ══╗")
        phase1_args = []
        if args.skip_videos:
            phase1_args.append("--skip-videos")

        import subprocess, sys
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "run_phase1.py")] + phase1_args,
            check=False,
            cwd=str(Path(__file__).resolve().parent.parent)
        )
        if result.returncode != 0:
            log.error("Phase 1 failed. Fix errors before continuing.")
            sys.exit(1)
        log.info("╚══ Phase 1 complete ══╝\n")

    # ── Phase 2 ──────────────────────────────────────────────────────────────
    if run_phase in (None, 2):
        log.info("╔══ PHASE 2: Deduplication + Balance ══╗")
        import subprocess, sys
        p2_args = [
            "--threshold", str(args.threshold),
            "--neg-ratio",  str(args.neg_ratio),
        ]
        if args.dry_run:
            p2_args.append("--dry-run")

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "run_phase2.py")] + p2_args,
            check=False,
            cwd=str(Path(__file__).resolve().parent.parent)
        )
        if result.returncode != 0:
            log.error("Phase 2 failed.")
            sys.exit(1)
        log.info("╚══ Phase 2 complete ══╝\n")

    # ── Phase 3 ──────────────────────────────────────────────────────────────
    if run_phase in (None, 3):
        log.info("╔══ PHASE 3: Training + Evaluation ══╗")
        import subprocess, sys
        p3_args = []
        if args.config_only:
            p3_args.append("--config-only")
        if args.eval_only:
            p3_args.append("--eval-only")

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "run_phase3.py")] + p3_args,
            check=False,
            cwd=str(Path(__file__).resolve().parent.parent)
        )
        if result.returncode != 0:
            log.error("Phase 3 failed.")
            sys.exit(1)
        log.info("╚══ Phase 3 complete ══╝\n")

    # ── Done ─────────────────────────────────────────────────────────────────
    elapsed = time.time() - t_global
    log.info(f"\n{'='*65}")
    log.info(f"  PIPELINE COMPLETE — {elapsed/3600:.1f} hours total")
    log.info(f"  Output dataset:   {BASE_OUT}")
    log.info(f"  Training runs:    /data/runs/weapon_detection/")
    log.info(f"  Best weights:     /data/runs/weapon_detection/<best_run>/weights/best.pt")
    log.info(f"  Eval report:      {BASE_OUT}/phase3_evaluation_report.json")
    log.info(f"{'='*65}\n")


if __name__ == "__main__":
    main()
