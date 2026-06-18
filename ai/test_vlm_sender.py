"""
test_vlm_sender.py  —  run this from your LOCAL machine or AWS instance
to test the /analyze endpoint with an existing video file.

Usage:
    python test_vlm_sender.py --video /data/shop.jpeg --url http://localhost:9000
    python test_vlm_sender.py --video /data/fight.mp4  --url http://<EC2-IP>:9000
"""

import argparse
import base64
import json
import sys
import httpx
import cv2
from datetime import datetime
from pathlib import Path


def extract_frames(path: str, max_frames: int = 5) -> list[str]:
    """Extract up to max_frames evenly-spaced frames, return as base64 JPEG strings."""
    p = Path(path)
    if not p.exists():
        sys.exit(f"File not found: {path}")

    suffix = p.suffix.lower()

    # --- image file ---
    if suffix in (".jpg", ".jpeg", ".png", ".bmp"):
        img = cv2.imread(str(p))
        if img is None:
            sys.exit(f"Could not read image: {path}")
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64 = base64.b64encode(buf).decode()
        return [b64]

    # --- video file ---
    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        sys.exit(f"Could not open video: {path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps   = cap.get(cv2.CAP_PROP_FPS) or 25
    print(f"  Video: {total} frames @ {fps:.1f} fps")

    indices = [int(total * i / max_frames) for i in range(max_frames)]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frames.append(base64.b64encode(buf).decode())
    cap.release()
    return frames


def send_to_vlm(frames: list[str], url: str, meta: dict) -> dict:
    payload = {"frames": frames, "metadata": meta}
    print(f"  Sending {len(frames)} frame(s) to {url}/analyze ...")
    try:
        with httpx.Client(timeout=180.0) as client:
            r = client.post(f"{url}/analyze", json=payload)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        sys.exit(f"HTTP {e.response.status_code}: {e.response.text}")
    except httpx.ConnectError:
        sys.exit(f"Could not connect to {url} — is the API running?")


def pretty_print(result: dict):
    print("\n" + "="*60)
    print(f"EVENT ID  : {result['event_id']}")
    print(f"TIMESTAMP : {result['timestamp']}")
    print(f"ZONE      : {result['zone']}  |  CAMERA: {result['camera_id']}")
    print(f"PEOPLE    : {result['people_count']}")
    print(f"VLM SCORE : {result['anomaly_score_vlm']}")
    print(f"FUSION    : {result['anomaly_score_fusion']}")
    print("\nOBSERVED EVENTS:")
    for e in result["observed_events"]:
        print(f"  - {e}")
    print("\nANOMALY EVIDENCE:")
    for e in result["anomaly_evidence"]:
        print(f"  - {e}")
    print(f"\nCAPTION:\n  {result['caption']}")
    print("="*60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video",    required=True, help="Path to video or image file")
    ap.add_argument("--url",      default="http://localhost:9000", help="Base URL of the VLM API")
    ap.add_argument("--zone",     default="zone-1")
    ap.add_argument("--camera",   default="cam-01")
    ap.add_argument("--score",    type=float, default=0.85, help="Fusion anomaly score (0-1)")
    ap.add_argument("--frames",   type=int,   default=5,   help="Max frames to extract")
    ap.add_argument("--save",     help="Optional: save JSON result to this file")
    args = ap.parse_args()

    print(f"\n[1] Extracting frames from: {args.video}")
    frames = extract_frames(args.video, args.frames)
    print(f"     Extracted {len(frames)} frame(s)")

    meta = {
        "camera_id":     args.camera,
        "zone":          args.zone,
        "timestamp":     datetime.utcnow().isoformat(),
        "anomaly_score": args.score,
        "clip_path":     args.video,
    }

    print(f"\n[2] Sending to VLM API")
    result = send_to_vlm(frames, args.url, meta)

    print("\n[3] Result")
    pretty_print(result)

    if args.save:
        with open(args.save, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved to {args.save}")


if __name__ == "__main__":
    main()