"""
converters/ds3_virat.py

Dataset: normal_dataset3_virat
S3 prefix: normal_dataset3_virat/videos/
Format: raw .mpg video files
Action: Download videos, extract 1 frame every N seconds → empty labels (negatives)

These are surveillance footage with no weapons — perfect negatives.
26 videos × ~3 min avg = ~80 min of footage → ~320 frames at 1/15s

Split: All → train
"""

import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_list_objects, s3_download, write_empty_label,
    BUCKET,
)

DATASET_NAME    = "ds3_virat"
S3_PREFIX       = "normal_dataset3_virat/videos/"
TARGET_SPLIT    = "train"
FRAME_INTERVAL  = 15   # extract 1 frame every 15 seconds
MAX_FRAMES_PER_VIDEO = 20  # cap per video to avoid overloading with one source


def extract_frames_ffmpeg(video_path: Path, out_dir: Path, interval: int, max_frames: int) -> list:
    """
    Use ffmpeg to extract frames at `interval` seconds.
    Returns list of extracted frame paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "frame_%05d.jpg"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"fps=1/{interval}",   # 1 frame per `interval` seconds
        "-q:v", "2",                   # JPEG quality 2 (high)
        "-frames:v", str(max_frames),
        str(pattern),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.warning(f"  ffmpeg error for {video_path.name}: {result.stderr[:200]}")

    return sorted(out_dir.glob("frame_*.jpg"))


def check_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def main():
    if not check_ffmpeg():
        log.error("ffmpeg not found. Install: sudo apt-get install ffmpeg")
        log.error("Skipping ds3_virat. Re-run after installing ffmpeg.")
        return

    log.info(f"[{DATASET_NAME}] Starting video → frame extraction...")
    stage      = staging_dir(DATASET_NAME)
    video_dir  = stage / "videos"
    frames_dir = stage / "frames"
    labels_dir = stage / "labels"

    # List all .mpg files in S3
    all_keys = s3_list_objects(S3_PREFIX)
    video_keys = [k for k in all_keys if k.lower().endswith(".mpg")]
    log.info(f"  Found {len(video_keys)} videos")

    manifest_rows = []
    total_frames  = 0

    for video_key in video_keys:
        video_name = Path(video_key).name
        video_local = video_dir / video_name

        # Download video
        log.info(f"  Downloading {video_name}...")
        s3_download(video_key, video_local)

        # Extract frames into per-video subdirectory
        vid_frames_dir = frames_dir / video_local.stem
        frames = extract_frames_ffmpeg(
            video_local, vid_frames_dir,
            interval=FRAME_INTERVAL,
            max_frames=MAX_FRAMES_PER_VIDEO,
        )
        log.info(f"  {video_name} → {len(frames)} frames extracted")

        for frame_path in frames:
            # Rename to include video name for uniqueness
            new_name = f"virat_{video_local.stem}_{frame_path.name}"
            final_img = stage / "images" / new_name
            final_img.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(frame_path, final_img)

            # Empty label (negative)
            lbl_path = labels_dir / (final_img.stem + ".txt")
            write_empty_label(lbl_path)

            manifest_rows.append({
                "image_path": str(final_img),
                "label_path": str(lbl_path),
                "split": TARGET_SPLIT,
                "dataset": DATASET_NAME,
                "is_negative": True,
            })
            total_frames += 1

        # Delete video to save disk space
        video_local.unlink(missing_ok=True)

    append_manifest(manifest_rows)
    log.info(
        f"[{DATASET_NAME}] Done. "
        f"{total_frames} negative frames extracted from {len(video_keys)} videos → train"
    )


if __name__ == "__main__":
    main()
