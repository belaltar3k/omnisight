"""
scripts/00_create_dirs.py
Create all output directories and reset the manifest.
Run this ONCE before any converter.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import BASE_OUT, STAGING, MANIFEST_CSV, SPLITS, log


def main():
    log.info("Creating unified dataset directory structure...")

    for split in SPLITS:
        for sub in ("images", "labels"):
            p = BASE_OUT / split / sub
            p.mkdir(parents=True, exist_ok=True)
            log.info(f"  ✓ {p}")

    STAGING.mkdir(parents=True, exist_ok=True)
    log.info(f"  ✓ {STAGING}")

    if MANIFEST_CSV.exists():
        MANIFEST_CSV.unlink()
        log.info("  ✓ Manifest reset")

    yaml_path = BASE_OUT / "data.yaml"
    yaml_content = f"""# Unified Weapon Detection Dataset
path: {BASE_OUT}
train: train/images
val:   val/images
test:  test/images

nc: 1
names:
  0: weapon
"""
    yaml_path.write_text(yaml_content)
    log.info(f"  ✓ {yaml_path}")

    log.info("Done. Run converters next.")


if __name__ == "__main__":
    main()
