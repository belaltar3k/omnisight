"""
converters/ds13_ucf_normal.py

Dataset: UCFDataset — normal videos only
S3 prefix: UCFDataset/videos/train/normal/
Format: .mp4 videos, NO labels — pure negatives

Action:
  - Download videos (or stream from S3)
  - Extract 1 frame every 30 seconds
  - Write empty label files (negatives)
  - Cap at MAX_FRAMES_PER_VIDEO to keep balance

These are the 800 Normal_Videos*.mp4 files — clean surveillance footage.
Split: All → train
"""

import sys
import subprocess
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.utils import (
    log, staging_dir, append_manifest,
    s3_list_objects, s3_download,
    write_empty_label,
)

DATASET_NAME        = "ds13_ucf_normal"
S3_PREFIX           = "UCFDataset/videos/train/normal/"
TARGET_SPLIT        = "train"
FRAME_INTERVAL_SEC  = 30    # 1 frame per 30s (avg video ~3-10min → 6-20 frames)
MAX_FRAMES_PER_VIDEO = 15   # hard cap per video


def check_ffmpeg() -> bool:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def extract_frames(video_path: Path, out_dir: Path, interval: int, max_frames: int) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "frame_%05d.jpg")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"fps=1/{interval}",
        "-q:v", "3",
        "-frames:v", str(max_frames),
        pattern,
    ]
    subprocess.run(cmd, capture_output=True)
    return sorted(out_dir.glob("frame_*.jpg"))


def main():
    if not check_ffmpeg():
        log.error("ffmpeg not found. Install: sudo apt-get install ffmpeg")
        log.error(f"Skipping {DATASET_NAME}.")
        return

    log.info(f"[{DATASET_NAME}] Extracting negative frames from UCF normal videos...")
    stage      = staging_dir(DATASET_NAME)
    video_dir  = stage / "videos"
    frames_dir = stage / "frames"
    out_img    = stage / "images"
    out_lbl    = stage / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    all_keys = s3_list_objects(S3_PREFIX)
    video_keys = [k for k in all_keys if k.lower().endswith(".mp4")]
    log.info(f"  Found {len(video_keys)} normal videos")

    manifest_rows = []
    total_frames  = 0

    for video_key in video_keys:
        video_name  = Path(video_key).name
        video_local = video_dir / video_name

        log.info(f"  Downloading {video_name}...")
        s3_download(video_key, video_local)

        vid_frames_dir = frames_dir / video_local.stem
        frames = extract_frames(
            video_local, vid_frames_dir,
            interval=FRAME_INTERVAL_SEC,
            max_frames=MAX_FRAMES_PER_VIDEO,
        )
        log.info(f"    {video_name}: {len(frames)} frames")

        for frame in frames:
            unique_name = f"ucfnorm_{video_local.stem}_{frame.name}"
            dst_img = out_img / unique_name
            dst_lbl = out_lbl / (dst_img.stem + ".txt")

            shutil.copy2(frame, dst_img)
            write_empty_label(dst_lbl)

            manifest_rows.append({
                "image_path": str(dst_img),
                "label_path": str(dst_lbl),
                "split": TARGET_SPLIT,
                "dataset": DATASET_NAME,
                "is_negative": True,
            })
            total_frames += 1

        # Free disk space immediately
        video_local.unlink(missing_ok=True)
        shutil.rmtree(vid_frames_dir, ignore_errors=True)

    append_manifest(manifest_rows)
    log.info(
        f"[{DATASET_NAME}] Done. "
        f"{total_frames} negative frames from {len(video_keys)} videos → train"
    )


if __name__ == "__main__":
    main()


# ─────────────────────────────────────────────────────────────────────────────
# Mall negatives (appended here since it's tiny)
# ─────────────────────────────────────────────────────────────────────────────
"""
converters/ds_mall_negatives.py  (inline — run via main_mall() below)

Dataset: normal_dataset1_mall
S3 prefix: normal_dataset1_mall/mall_dataset/frames/
Format: sequential .jpg frames (seq_000001.jpg ... 2000+)
Action:
  - Subsample 1 in every 30 frames (mall footage changes slowly)
  - Empty labels (negatives)
Split: train
"""


def main_mall():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from data.utils import (
        log, staging_dir, append_manifest,
        s3_list_objects, s3_download,
        write_empty_label,
    )
    import shutil

    MALL_DATASET_NAME = "ds_mall_negatives"
    MALL_S3_PREFIX    = "normal_dataset1_mall/mall_dataset/frames/"
    SUBSAMPLE_EVERY   = 30   # take 1 frame per 30 (mall sequence is very redundant)

    log.info(f"[{MALL_DATASET_NAME}] Extracting mall negative frames...")
    stage   = staging_dir(MALL_DATASET_NAME)
    raw_dir = stage / "raw"
    out_img = stage / "images"
    out_lbl = stage / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    all_keys = s3_list_objects(MALL_S3_PREFIX)
    img_keys = sorted([k for k in all_keys if k.lower().endswith(".jpg")])
    log.info(f"  Found {len(img_keys)} frames, subsampling 1/{SUBSAMPLE_EVERY}")

    selected_keys = img_keys[::SUBSAMPLE_EVERY]
    manifest_rows = []

    for key in selected_keys:
        fname     = Path(key).name
        local_raw = raw_dir / fname
        s3_download(key, local_raw)

        dst_img = out_img / f"mall_{fname}"
        dst_lbl = out_lbl / (dst_img.stem + ".txt")
        shutil.copy2(local_raw, dst_img)
        write_empty_label(dst_lbl)

        manifest_rows.append({
            "image_path": str(dst_img),
            "label_path": str(dst_lbl),
            "split": "train",
            "dataset": MALL_DATASET_NAME,
            "is_negative": True,
        })

    append_manifest(manifest_rows)
    log.info(f"[{MALL_DATASET_NAME}] Done. {len(manifest_rows)} negative frames → train")


if __name__ == "__main__":
    # This file handles both UCF normal AND mall negatives
    main()
    main_mall()
