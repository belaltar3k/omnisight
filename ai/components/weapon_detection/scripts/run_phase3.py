"""
phase3/run_phase3.py

Phase 3 Master Runner — Full Iterative Training Loop

Execution order:
  1. Generate config files (hyperparams, augmentation, training scripts)
  2. Train v1 baseline (YOLOv11x, 100 epochs, 1280px)
  3. Hard negative mining round 1
  4. Train v2 with mined negatives (50 epochs, fine-tune from v1)
  5. Hard negative mining round 2
  6. Train v3 (optional third round if gains > 1 mAP)
  7. SAHI evaluation on best model vs test set
  8. Final report

Usage:
    python phase3/run_phase3.py                  # full loop
    python phase3/run_phase3.py --config-only    # just write config files
    python phase3/run_phase3.py --eval-only      # just evaluate existing model
    python phase3/run_phase3.py --skip-v1        # skip v1 training (already done)
    python phase3/run_phase3.py --mining-rounds 3  # do 3 mining rounds
"""

import sys
import time
import argparse
import subprocess
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import log, BASE_OUT

RUNS_DIR   = Path("/data/runs/weapon_detection")
PHASE3_DIR = Path(__file__).parent


def check_gpu():
    try:
        import torch
        if not torch.cuda.is_available():
            log.warning("No CUDA GPU detected. Training will be extremely slow on CPU.")
            return False
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb  = torch.cuda.get_device_properties(0).total_memory / 1e9
        log.info(f"  GPU: {gpu_name} ({vram_gb:.1f} GB VRAM)")
        if vram_gb < 16:
            log.warning(
                f"  Only {vram_gb:.1f}GB VRAM detected. "
                "Reduce batch size or imgsz if OOM errors occur."
            )
        return True
    except ImportError:
        log.error("PyTorch not installed. Run: pip install torch torchvision")
        return False


def check_ultralytics():
    try:
        import ultralytics
        log.info(f"  ultralytics: {ultralytics.__version__}")
        return True
    except ImportError:
        log.error("ultralytics not installed. Run: pip install ultralytics>=8.3.0")
        return False


def check_dataset():
    """Verify phase 1+2 completed successfully."""
    required = [
        BASE_OUT / "data.yaml",
        BASE_OUT / "train" / "images",
        BASE_OUT / "val"   / "images",
        BASE_OUT / "test"  / "images",
    ]
    missing = [p for p in required if not p.exists()]
    if missing:
        log.error("Phase 1/2 output missing:")
        for p in missing:
            log.error(f"  {p}")
        log.error("Run phase 1 and phase 2 first.")
        return False

    # Count images
    for split in ("train", "val", "test"):
        n = len(list((BASE_OUT / split / "images").glob("*.*")))
        log.info(f"  {split}: {n:,} images")

    return True


def best_weights_path(version: str) -> Path:
    return RUNS_DIR / version / "weights" / "best.pt"


def weights_exist(version: str) -> bool:
    return best_weights_path(version).exists()


def train_model(version: str, script_name: str) -> bool:
    """Run a training script. Returns True if successful."""
    script_path = PHASE3_DIR / script_name
    if not script_path.exists():
        log.error(f"Training script not found: {script_path}")
        return False

    log.info(f"  Launching: bash {script_path}")
    result = subprocess.run(["bash", str(script_path)], check=False)
    if result.returncode != 0:
        log.error(f"  Training failed (exit {result.returncode})")
        return False

    if not weights_exist(version):
        log.error(f"  Training completed but best.pt not found for {version}")
        return False

    log.info(f"  ✓ {version} training complete: {best_weights_path(version)}")
    return True


def run_mining(model_version: str, round_num: int, dry_run: bool = False) -> int:
    """Run hard negative mining. Returns number of new negatives added."""
    
    log.info(f"  Mining round {round_num} from {model_version}...")
    mine_main(
        model_version=model_version,
        mining_round=round_num,
        dry_run=dry_run,
    )
    # Count newly added mined images
    mined_dir = BASE_OUT / "mined_hard_negatives" / f"round_{round_num}" / "images"
    if mined_dir.exists():
        n = len(list(mined_dir.glob("*.*")))
        log.info(f"  ✓ Mining round {round_num}: {n:,} hard negatives added")
        return n
    return 0


def get_best_map(version: str) -> float:
    """Extract best mAP50 from training results CSV."""
    results_csv = RUNS_DIR / version / "results.csv"
    if not results_csv.exists():
        return 0.0
    try:
        import csv
        with open(results_csv) as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return 0.0
        # Header may have spaces: '      metrics/mAP50(B)'
        map_key = next(
            (k for k in rows[0].keys() if "mAP50" in k and "95" not in k),
            None
        )
        if map_key is None:
            return 0.0
        values = [float(r[map_key]) for r in rows if r[map_key].strip()]
        return max(values) if values else 0.0
    except Exception:
        return 0.0


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Training Loop")
    parser.add_argument("--config-only",    action="store_true",
                        help="Only write config files, don't train")
    parser.add_argument("--eval-only",      action="store_true",
                        help="Only run SAHI evaluation on existing model")
    parser.add_argument("--skip-v1",        action="store_true",
                        help="Skip v1 training (use if already trained)")
    parser.add_argument("--skip-v2",        action="store_true",
                        help="Skip v2 training")
    ")
    parser.add_argument("--dry-run-mining", action="store_true",
                        help="Preview mining without adding files")
    parser.add_argument("--eval-version",   default=None,
                        help="Which run version to evaluate (default: best available)")
    args = parser.parse_args()

    t_start = time.time()
    log.info("\n" + "="*65)
    log.info("  PHASE 3 — TRAINING + HARD NEGATIVE MINING + EVALUATION")
    log.info("="*65)

    # ── Pre-flight checks ─────────────────────────────────────────────────────
    log.info("\n── Pre-flight checks ──")
    if not args.eval_only and not args.config_only:
        if not check_gpu():
            log.warning("Proceeding without GPU (very slow)...")
        if not check_ultralytics():
            sys.exit(1)
    if not check_dataset():
        sys.exit(1)

    # ── Step 1: Generate config ───────────────────────────────────────────────
    log.info("\n── Step 1: Generating config files ──")
    from config.settings import main as gen_config
    gen_config()

    if args.config_only:
        log.info("Config-only mode. Done.")
        return

    if args.eval_only:
        # Jump straight to evaluation
        eval_version = args.eval_version or (
            "v2_hardneg" if weights_exist("v2_hardneg") else "v1_baseline"
        )
        log.info(f"\n── Evaluation only: {eval_version} ──")
        from inference.evaluate_sahi import main as eval_main
        eval_main(model_version=eval_version)
        return

    # ── Tracking ─────────────────────────────────────────────────────────────
    run_log = {
        "start_time": datetime.now().isoformat(),
        "versions": {},
    }

    # ── Step 2: Train v1 baseline ─────────────────────────────────────────────
    if not args.skip_v1:
        log.info("\n── Step 2: Training v1 baseline ──")
        log.info("  YOLOv11x | 100 epochs | 1280px | batch=8")
        ok = train_model("v1_baseline", "train_v1_baseline.sh")
        if not ok:
            log.error("v1 training failed. Cannot continue.")
            sys.exit(1)
        v1_map = get_best_map("v1_baseline")
        log.info(f"  v1 best mAP50: {v1_map:.4f}")
        run_log["versions"]["v1_baseline"] = {"mAP50": v1_map}
    else:
        log.info("\n── Step 2: Skipping v1 (--skip-v1) ──")
        if not weights_exist("v1_baseline"):
            log.error("v1 weights not found and --skip-v1 set. Cannot mine.")
            sys.exit(1)
        v1_map = get_best_map("v1_baseline")
        log.info(f"  Existing v1 mAP50: {v1_map:.4f}")

    # ── Steps 3+4: Mining loop ────────────────────────────────────────────────
    current_version = "v1_baseline"
    prev_map        = v1_map

    for round_num in range(1, args.mining_rounds + 1):
        log.info(f"\n── Mining Round {round_num} / {args.mining_rounds} ──")
        n_mined = run_mining(
            model_version=current_version,
            round_num=round_num,
            dry_run=args.dry_run_mining,
        )
        run_log["versions"][current_version][f"mining_round_{round_num}"] = n_mined

        if n_mined == 0 and not args.dry_run_mining:
            log.info("  No new false positives found. Model is already robust. Stopping loop.")
            break

        if args.skip_v2 and round_num == 1:
            log.info("  --skip-v2 set, skipping retraining.")
            break

        # Retrain
        next_version = f"v{round_num + 1}_hardneg"
        log.info(f"\n── Training {next_version} ──")

        # For round > 1, modify the v2 script to load from current_version
        if round_num > 1:
            # Patch the v2 script weights path dynamically
            v2_script = PHASE3_DIR / "train_v2_hardneg.sh"
            original  = v2_script.read_text()
            patched   = original.replace(
                "v1_baseline/weights/best.pt",
                f"{current_version}/weights/best.pt"
            ).replace(
                'name="v2_hardneg"',
                f'name="{next_version}"'
            )
            v2_script.write_text(patched)

        ok = train_model(next_version, "train_v2_hardneg.sh")
        if not ok:
            log.error(f"{next_version} training failed.")
            break

        new_map = get_best_map(next_version)
        gain    = new_map - prev_map
        log.info(f"  {next_version} mAP50: {new_map:.4f} (Δ {gain:+.4f} vs {current_version})")
        run_log["versions"][next_version] = {"mAP50": new_map, "map_gain": round(gain, 4)}

        current_version = next_version
        prev_map        = new_map

        if gain < 0.005 and round_num >= 2:
            log.info(f"  Gain below 0.5 mAP — converged. Stopping loop.")
            break

    # ── Step 5: Final SAHI evaluation ─────────────────────────────────────────
    log.info(f"\n── Step 5: SAHI Evaluation — {current_version} ──")
    try:
        from inference.evaluate_sahi import main as eval_main
        eval_main(model_version=current_version)
    except Exception as e:
        log.error(f"SAHI evaluation failed: {e}")
        log.info("You can run it manually: python phase3/evaluate_sahi.py")

    # ── Final summary ─────────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    run_log["end_time"]        = datetime.now().isoformat()
    run_log["elapsed_hours"]   = round(elapsed / 3600, 2)
    run_log["best_version"]    = current_version
    run_log["best_mAP50"]      = prev_map

    log.info(f"\n{'='*65}")
    log.info(f"  PHASE 3 COMPLETE")
    log.info(f"  Best version:  {current_version}")
    log.info(f"  Best mAP50:    {prev_map:.4f}")
    log.info(f"  Total runtime: {elapsed/3600:.1f} hours")
    log.info(f"{'='*65}")
    log.info(f"\nBest model weights:")
    log.info(f"  {best_weights_path(current_version)}")
    log.info(f"\nEvaluation report:")
    log.info(f"  {BASE_OUT}/phase3_evaluation_report.json")

    # Save run log
    run_log_path = BASE_OUT / "phase3_run_log.json"
    run_log_path.write_text(json.dumps(run_log, indent=2))
    log.info(f"\nRun log: {run_log_path}")


if __name__ == "__main__":
    main()
