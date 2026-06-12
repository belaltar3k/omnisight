"""
Builds the unified dataset from raw source files.

Scans all configured dataset directories, parses every video with the
appropriate parser, stacks frames into (T, M, 17, 3) arrays, saves them
as .npy files, and writes train_index.json / val_index.json.

Usage:
    python scripts/build_dataset.py
"""

import os
import re
import json
import random
import traceback

import numpy as np
from tqdm import tqdm

from ..config   import Config
from .taxonomy  import LABEL_MAP, NTU_MAPPING
from .parsers   import (
    parse_yolo_json,
    parse_alphapose_json,
    parse_hrcrime_csv,
    parse_ntu_skeleton,
    pad_and_stack,
)


def build(cfg: Config | None = None) -> None:
    cfg = cfg or Config()

    save_dir = os.path.join(cfg.unified_dir, "videos")
    os.makedirs(save_dir, exist_ok=True)

    videos_metadata: list[dict] = []
    vid_counter   = 0
    error_count   = 0

    # ── Helper ───────────────────────────────────────────────────

    def _save_video(raw_poses, label, fps, scene_id):
        nonlocal vid_counter
        stacked = pad_and_stack(raw_poses, cfg.max_bodies)
        if stacked is None:
            return
        T = stacked.shape[0]
        if T < 8:
            return
        path = os.path.join(save_dir, f"vid_{vid_counter:06d}.npy")
        np.save(path, stacked)
        videos_metadata.append(
            {"path": path, "label": label, "fps": fps, "T": T, "scene_id": scene_id}
        )
        vid_counter += 1

    # ── Build task queue ─────────────────────────────────────────

    print("🔎  Scanning directories to build task queue …")
    tasks: list[tuple] = []

    # DS14 — HR-Crime (CSV, 30 FPS)
    ds14 = os.path.join(cfg.data_root, "dataset14_hr_crime")
    if os.path.exists(ds14):
        for root, _, files in os.walk(ds14):
            parent = os.path.basename(os.path.dirname(root))
            if parent not in LABEL_MAP:
                continue
            scene_id = f"ds14__{os.path.basename(root)}"
            for f in files:
                if f.startswith(".") or not f.endswith(".csv"):
                    continue
                tasks.append((
                    os.path.join(root, f),
                    parse_hrcrime_csv,
                    LABEL_MAP[parent],
                    30.0,
                    scene_id,
                ))

    # YOLO-JSON datasets (frame-first, COCO-17)
    yolo_sources = [
        ("dataset3_fight_surv/dataset3_extracted_poses",           25.0, 0),
        ("dataset4_real_life_violence/dataset4_extracted_poses",   30.0, 0),
        ("dataset7_firearm_actions/dataset7_extracted_poses",      30.0, 0),
        ("dataset9_shoplifting_video/dataset9_extracted_poses",    30.0, 0),
        ("dataset10_shoplifting_videos/dataset10_extracted_poses", 25.0, 0),
    ]
    for ds_folder, fps, depth in yolo_sources:
        ds_tag = ds_folder.split("/")[0]
        base   = os.path.join(cfg.data_root, ds_folder)
        if not os.path.exists(base):
            continue
        for root, _, files in os.walk(base):
            parts = os.path.relpath(root, base).split(os.sep)
            cls   = parts[depth] if len(parts) > depth else None
            if not cls or cls not in LABEL_MAP:
                continue
            scene_id = f"{ds_tag}__{os.path.basename(root)}"
            for f in files:
                if f.startswith(".") or not f.endswith(".json"):
                    continue
                tasks.append((
                    os.path.join(root, f),
                    parse_yolo_json,
                    LABEL_MAP[cls],
                    fps,
                    scene_id,
                ))

    # DS8 — PoseLift, AlphaPose (label = Normal)
    ds8_base = os.path.join(
        cfg.data_root,
        "dataset8_poselift/dataset8_extracted_poses/Json_files/data/PoseLift/pose",
    )
    if os.path.exists(ds8_base):
        for root, _, files in os.walk(ds8_base):
            scene_id = f"dataset8_poselift__{os.path.basename(root)}"
            for f in files:
                if f.startswith(".") or not f.endswith(".json"):
                    continue
                tasks.append((
                    os.path.join(root, f),
                    parse_alphapose_json,
                    0,
                    30.0,
                    scene_id,
                ))

    # DS13 — RetailS, AlphaPose (label = Anomaly)
    ds13_base = os.path.join(cfg.data_root, "dataset13_retails/RetailS")
    if os.path.exists(ds13_base):
        for root, _, files in os.walk(ds13_base):
            scene_id = f"dataset13_retails__{os.path.basename(root)}"
            for f in files:
                if f.startswith(".") or not f.endswith(".json"):
                    continue
                tasks.append((
                    os.path.join(root, f),
                    parse_alphapose_json,
                    1,
                    30.0,
                    scene_id,
                ))

    # DS1 — NTU RGB+D (Kinect v2, 30 FPS)
    ds1_dir = os.path.join(cfg.data_root, "dataset1_ntu_rgbd")
    if os.path.exists(ds1_dir):
        for fname in os.listdir(ds1_dir):
            if fname.startswith(".") or not fname.endswith(".skeleton"):
                continue
            m     = re.search(r"A(\d{3})\.skeleton$", fname)
            act   = f"A{m.group(1)}" if m else None
            label = NTU_MAPPING.get(act, 0) if act else 0
            tasks.append((
                os.path.join(ds1_dir, fname),
                parse_ntu_skeleton,
                label,
                30.0,
                f"ntu__{fname[:4]}",
            ))

    # ── Process all tasks ────────────────────────────────────────

    print(f"🚀  Found {len(tasks)} files. Compiling unified dataset …")
    for path, parser, label, fps, scene_id in tqdm(tasks, desc="Building"):
        try:
            _save_video(parser(path), label, fps, scene_id)
        except Exception:
            error_count += 1

    print(f"\n✅  {vid_counter} videos saved  |  ❌ {error_count} errors")

    # ── Scene-level 80 / 20 train-val split ──────────────────────

    random.seed(cfg.seed)
    unique_scenes = list({v["scene_id"] for v in videos_metadata})
    random.shuffle(unique_scenes)
    n_train       = int(len(unique_scenes) * 0.8)
    train_scenes  = set(unique_scenes[:n_train])

    train_index = [v for v in videos_metadata if v["scene_id"] in train_scenes]
    val_index   = [v for v in videos_metadata if v["scene_id"] not in train_scenes]

    print(
        f"\n📁  Split → train={len(train_index)} videos "
        f"({n_train} scenes)  |  "
        f"val={len(val_index)} videos "
        f"({len(unique_scenes) - n_train} scenes)"
    )

    os.makedirs(cfg.unified_dir, exist_ok=True)
    for name, index in [("train_index", train_index), ("val_index", val_index)]:
        with open(os.path.join(cfg.unified_dir, f"{name}.json"), "w") as fh:
            json.dump(index, fh)

    print("✅  Index files written. Ready for training.")