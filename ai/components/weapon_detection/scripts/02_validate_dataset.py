"""
scripts/02_validate_dataset.py

Full integrity check on the merged dataset:
  1. Every image has a label file
  2. Every label file has a corresponding image
  3. Label format is valid YOLO (5 fields, normalized values in [0,1])
  4. No corrupt / unreadable images
  5. Class ids are all 0 (weapon only)
  6. Bounding boxes are sane (w > 0, h > 0, cx+w/2 <= 1, etc.)
  7. Report statistics per split

Writes a detailed error report to:
  /data/datasets/unified/validation_report.txt
"""

import sys
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import log, BASE_OUT, SPLITS

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False
    log.warning("Pillow not installed — skipping image corruption check")

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
REPORT_PATH = BASE_OUT / "validation_report.txt"

errors   = []
warnings = []


def check_label(lbl_path: Path) -> list:
    """Check one label file. Returns list of error strings."""
    errs = []
    try:
        lines = lbl_path.read_text().strip().splitlines()
    except Exception as e:
        return [f"Cannot read label: {e}"]

    for i, line in enumerate(lines):
        if not line.strip():
            continue
        parts = line.strip().split()
        if len(parts) != 5:
            errs.append(
                f"Line {i+1}: expected 5 fields, got {len(parts)} "
                f"(possible OBB/polygon) → '{line[:60]}'"
            )
            continue
        try:
            cls = int(parts[0])
            cx, cy, w, h = [float(x) for x in parts[1:]]
        except ValueError as e:
            errs.append(f"Line {i+1}: parse error — {e}")
            continue

        if cls != 0:
            errs.append(f"Line {i+1}: unexpected class {cls} (expected 0)")
        if not (0 <= cx <= 1 and 0 <= cy <= 1):
            errs.append(f"Line {i+1}: cx/cy out of [0,1]: cx={cx:.4f} cy={cy:.4f}")
        if not (0 < w <= 1 and 0 < h <= 1):
            errs.append(f"Line {i+1}: w/h invalid: w={w:.4f} h={h:.4f}")
        if cx + w / 2 > 1.01 or cy + h / 2 > 1.01:
            errs.append(f"Line {i+1}: bbox extends beyond image boundary")

    return errs


def check_image(img_path: Path) -> str | None:
    """Returns error string if image is unreadable, else None."""
    if not PIL_OK:
        return None
    try:
        with Image.open(img_path) as im:
            im.verify()
        return None
    except Exception as e:
        return str(e)


def main():
    log.info("Starting dataset validation...")
    report_lines = ["WEAPON DATASET VALIDATION REPORT", "=" * 60, ""]

    total_errors   = 0
    total_warnings = 0

    for split in SPLITS:
        img_dir = BASE_OUT / split / "images"
        lbl_dir = BASE_OUT / split / "labels"

        if not img_dir.exists():
            log.warning(f"  {split}/images/ does not exist, skipping")
            continue

        img_files = sorted(
            f for f in img_dir.glob("*.*")
            if f.suffix.lower() in IMAGE_EXTS
        )
        lbl_files = {f.stem for f in lbl_dir.glob("*.txt")} if lbl_dir.exists() else set()

        n_images        = len(img_files)
        n_positives     = 0
        n_negatives     = 0
        n_corrupt       = 0
        n_missing_label = 0
        n_label_errors  = 0
        n_orphan_labels = 0
        split_errors    = []

        log.info(f"\n  Checking {split}: {n_images} images...")

        for img_path in tqdm(img_files, desc=f"  {split}", leave=False):
            # Check image readability
            img_err = check_image(img_path)
            if img_err:
                n_corrupt += 1
                split_errors.append(f"CORRUPT IMAGE: {img_path.name} — {img_err}")
                continue

            # Check label exists
            lbl_path = lbl_dir / (img_path.stem + ".txt")
            if not lbl_path.exists():
                n_missing_label += 1
                split_errors.append(f"MISSING LABEL: {img_path.name}")
                continue

            # Check label content
            lbl_errors = check_label(lbl_path)
            if lbl_errors:
                n_label_errors += 1
                for e in lbl_errors:
                    split_errors.append(f"LABEL ERROR [{img_path.stem}]: {e}")

            # Count positive vs negative
            content = lbl_path.read_text().strip()
            if content:
                n_positives += 1
            else:
                n_negatives += 1

        # Check for orphan labels (labels with no image)
        img_stems = {f.stem for f in img_files}
        for lbl_stem in lbl_files:
            if lbl_stem not in img_stems:
                n_orphan_labels += 1
                split_errors.append(f"ORPHAN LABEL: {lbl_stem}.txt")

        # Write split summary
        neg_pct = (n_negatives / n_images * 100) if n_images > 0 else 0
        summary = (
            f"\n[{split.upper()}]\n"
            f"  Total images:   {n_images}\n"
            f"  Positive:       {n_positives} ({100-neg_pct:.1f}%)\n"
            f"  Negative:       {n_negatives} ({neg_pct:.1f}%)\n"
            f"  Corrupt images: {n_corrupt}\n"
            f"  Missing labels: {n_missing_label}\n"
            f"  Label errors:   {n_label_errors}\n"
            f"  Orphan labels:  {n_orphan_labels}\n"
        )
        report_lines.append(summary)
        log.info(summary)

        if split_errors:
            report_lines.append(f"  Errors ({len(split_errors)}):")
            for e in split_errors[:50]:  # show first 50 in report
                report_lines.append(f"    {e}")
            if len(split_errors) > 50:
                report_lines.append(f"    ... and {len(split_errors)-50} more (see full report)")
            total_errors += len(split_errors)

        total_warnings += n_corrupt + n_missing_label + n_orphan_labels

    # Final
    report_lines.append("\n" + "=" * 60)
    report_lines.append(f"TOTAL ERRORS:   {total_errors}")
    report_lines.append(f"TOTAL WARNINGS: {total_warnings}")
    if total_errors == 0:
        report_lines.append("STATUS: ✓ PASSED — dataset is clean")
    else:
        report_lines.append("STATUS: ✗ ISSUES FOUND — review errors above")

    report_text = "\n".join(report_lines)
    REPORT_PATH.write_text(report_text)
    log.info(f"\nValidation report saved: {REPORT_PATH}")

    if total_errors == 0:
        log.info("✓ Dataset passed validation!")
    else:
        log.warning(f"✗ {total_errors} issues found. Review {REPORT_PATH}")


if __name__ == "__main__":
    main()
