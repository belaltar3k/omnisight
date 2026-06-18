"""
Setup script for OmniSight Smart City Analytics Platform.
Downloads required models and creates directory structure.
"""
from __future__ import annotations

import os
import sys


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Create directories
    dirs = [
        os.path.join(base_dir, "output"),
        os.path.join(base_dir, "alerts"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"  Directory: {d}")

    # Check primary YOLO model
    print("\n--- Model Check ---")
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        print("  yolov8n.pt: OK (auto-downloaded by ultralytics)")
    except Exception as e:
        print(f"  yolov8n.pt: will be downloaded on first run ({e})")

    # Check optional dependencies
    print("\n--- Optional Dependencies ---")
    optional = {
        "scipy": "Crowd analysis, queue detection, flow anomaly",
    }
    for pkg, desc in optional.items():
        try:
            __import__(pkg)
            print(f"  {pkg}: OK ({desc})")
        except ImportError:
            print(f"  {pkg}: NOT INSTALLED — {desc} will be limited")

    print("\n--- Setup Complete ---")
    print(f"Run: python {os.path.join(base_dir, 'main.py')} --source <video.mp4>")
    print(f"Demo: python {os.path.join(base_dir, 'main.py')} --demo")


if __name__ == "__main__":
    main()
