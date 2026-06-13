"""
Setup script: clone FlexSED repository and install its dependencies.

Run this once before using the PAAN inference pipeline.

Usage:
    python scripts/setup_flexsed.py
    python scripts/setup_flexsed.py --target ../FlexSED
"""

import argparse
import subprocess
import sys
from pathlib import Path


FLEXSED_REPO = "https://github.com/JHU-LCAP/FlexSED.git"


def setup(target_dir: Path) -> None:
    if target_dir.exists():
        print(f"FlexSED already exists at {target_dir}")
    else:
        print(f"Cloning FlexSED into {target_dir} ...")
        subprocess.check_call(["git", "clone", FLEXSED_REPO, str(target_dir)])

    req = target_dir / "requirements.txt"
    if req.exists():
        print("Installing FlexSED requirements ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)])

    print("FlexSED setup complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clone and install FlexSED dependency.")
    default_target = Path(__file__).resolve().parent.parent / "FlexSED"
    parser.add_argument("--target", type=Path, default=default_target, help="Target directory")
    args = parser.parse_args()
    setup(args.target)
