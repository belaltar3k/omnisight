"""
Setup script: download YOLO model weights and verify dependencies.

Run this once before using the MTMCT tracking pipeline.

Usage:
    python scripts/setup.py
    python scripts/setup.py --model yolov8m.pt
"""

import argparse
import subprocess
import sys
from pathlib import Path


YOLO_MODELS = {
    "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
    "yolov8s.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s.pt",
    "yolov8m.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8m.pt",
}


def check_dependencies() -> None:
    print("Checking Python dependencies...")
    req_file = Path(__file__).resolve().parent.parent / "requirements.txt"
    if req_file.exists():
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)]
        )
        print("All dependencies installed.")
    else:
        print(f"WARNING: requirements.txt not found at {req_file}")


def download_model(model_name: str, target_dir: Path) -> Path:
    target_path = target_dir / model_name
    if target_path.exists():
        print(f"Model already exists: {target_path}")
        return target_path

    if model_name in YOLO_MODELS:
        url = YOLO_MODELS[model_name]
        print(f"Downloading {model_name} from {url}...")
        import urllib.request
        urllib.request.urlretrieve(url, str(target_path))
        print(f"Saved to: {target_path}")
    else:
        print(f"Attempting to load {model_name} via ultralytics (will auto-download)...")
        from ultralytics import YOLO
        YOLO(model_name)
        print(f"Model {model_name} ready.")

    return target_path


def verify_gpu() -> None:
    try:
        import torch
        if torch.cuda.is_available():
            print(f"GPU available: {torch.cuda.get_device_name(0)}")
            print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
        else:
            print("WARNING: No CUDA GPU detected. Running on CPU will be slow.")
    except ImportError:
        print("WARNING: PyTorch not installed.")


def main():
    parser = argparse.ArgumentParser(description="Setup MTMCT tracking dependencies.")
    parser.add_argument(
        "--model", default="yolov8s.pt",
        help="YOLO model to download (default: yolov8s.pt)"
    )
    parser.add_argument(
        "--skip-deps", action="store_true",
        help="Skip pip dependency installation"
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    if not args.skip_deps:
        check_dependencies()

    print()
    verify_gpu()

    print()
    download_model(args.model, project_root)

    print("\nSetup complete. Run inference with:")
    print(f"  python inference/video_inference.py --videos cam1.mp4 cam2.mp4")


if __name__ == "__main__":
    main()
