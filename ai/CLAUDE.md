# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the pipeline

```bash
cd ai
python run_pipeline.py --video path/to/video.mp4 --device cuda
```

Key flags:
- `--threshold 0.55` — anomaly decision threshold (default 0.55)
- `--disable paan weapon_detection` — skip specific components
- `--no-plot` — skip matplotlib chart
- `--json output/result.json` — save JSON summary
- `--weights-dir path/to/weights/` — override weights location (default `ai/weights/`)

## Running individual components

Each component has a standalone inference entry point:

```bash
cd ai
python -m components.crime_skelnet.inference.video_inference --video input.mp4
python -m components.video_mae.inference.video_inference --video input.mp4
python -m components.paan.inference.run_paan --audio input.wav
python -m components.tracking.inference.video_inference --video input.mp4
```

Weapon detection evaluation uses SAHI tiled inference:
```bash
python -m components.weapon_detection.inference.evaluate_sahi
```

## Training

Each component has its own training script:
```bash
python components/crime_skelnet/scripts/train.py
python components/video_mae/scripts/train.py
```

Weapon detection has a multi-phase data pipeline (`scripts/00_*.py` through `03_*.py`) that must run before training.

## Dependencies

There is no unified `requirements.txt`. Each component has its own at `components/<name>/requirements.txt`. The pipeline mixes frameworks:

- **PyTorch**: crime_skelnet, video_mae, weapon_detection, tracking
- **TensorFlow**: paan (YAMNet via TF Hub)
- **Ultralytics**: crime_skelnet (YOLOv8-pose), weapon_detection (YOLOv11x), tracking (YOLOv8s)
- **HuggingFace Transformers**: video_mae (VideoMAE-Large), paan (Swin gunshot classifier)

## Architecture

### Overview

The AI module detects anomalies in surveillance video by running 4 independent detectors and fusing their per-frame scores with a weighted combination. A 5th component (tracking) assigns persistent identities to flagged individuals but does **not** contribute to the anomaly score.

### Pipeline data flow

```
video.mp4
  ├─→ CrimeSkelNet  (skeleton-based, weight=0.35)  → per-frame scores [0,1]
  ├─→ PAAN          (audio 3-stage,   weight=0.25)  → per-frame scores [0,1]
  ├─→ WeaponDetector (YOLO+SAHI,      weight=0.25)  → per-frame scores [0,1]
  ├─→ VideoMAE       (appearance,     weight=0.15)  → per-frame scores [0,1]
  └─→ WeightedFusionEngine
       → weighted sum → smoothing → threshold (0.55)
       → PipelineResult (anomaly regions, per-component breakdown)
```

VideoMAE has 94% AUC on UCF-Crime but degrades on domain shift — hence the low weight. CrimeSkelNet, PAAN, and weapon detection are more domain-robust.

### Pipeline module (`ai/pipeline/`)

- **`base.py`** — `BaseDetector` ABC and `DetectorResult` dataclass. Every detector implements `load(device)` and `predict(video_path) -> Optional[DetectorResult]`.
- **`detectors/`** — Adapter wrappers that import from `components/` and conform to `BaseDetector`. Each wrapper handles sys.path setup, model loading, and score formatting.
- **`fusion.py`** — `WeightedFusionEngine`: re-normalizes weights when components are unavailable (e.g., PAAN returns `None` if no audio track), aligns score arrays via `np.interp`, applies moving-average smoothing.
- **`runner.py`** — `PipelineRunner`: builds detectors from a registry, runs them sequentially (GPU VRAM constraint), catches per-detector failures without aborting the pipeline.
- **`config.py`** — `PipelineConfig` dataclass with weights, thresholds, model paths, device, and disabled list.
- **`result.py`** — `PipelineResult` and `AnomalyRegion` dataclasses.

### Adding a new detector

1. Create `components/<name>/` with config, models, inference subdirectories.
2. Create `pipeline/detectors/<name>_detector.py` implementing `BaseDetector`.
3. Add it to `pipeline/detectors/__init__.py`.
4. Add a factory entry in the `_default_registry()` dict in `runner.py`.
5. Add a weight entry in `PipelineConfig.weights`.
6. Add any weight-path fields to `PipelineConfig`.

The fusion engine dynamically re-normalizes — no changes needed there.

### Component internals

Each component follows the same directory pattern: `config/`, `models/`, `inference/`, and optionally `data/`, `training/`, `scripts/`.

**CrimeSkelNet**: 5-stream GCN (joint, bone, motion, bone-motion, angle). Uses YOLOv8x-pose + BoT-SORT for skeleton extraction, then sliding-window inference (4s clips, 32 frames). Input shape: `(B, 5, 3, 32, 17, 2)` — 5 streams, 3 channels, 32 frames, 17 COCO joints, 2 bodies.

**VideoMAE**: Frozen VideoMAE-Large extracts 1024-D clip embeddings → pooled to 32 snippets → CrimeTransformer (4-layer, 8-head) produces per-snippet anomaly scores + 14-class crime logits.

**PAAN**: 3-stage audio pipeline. Stage 1: YAMNet coarse filter. Stage 2: Swin spectrogram classifier for gunshot verification. Stage 3: FlexSED zero-shot semantic event detection. Returns a single combined score broadcast to all frames.

**Weapon Detection**: YOLOv11x with SAHI tiled inference. Samples at 2 FPS, forward-fills scores to adjacent frames. Trained on 12 unified datasets.

**Tracking (MTMCT)**: YOLOv8 + ByteTrack per camera, InsightFace (512-D face) + OSNet (512-D appearance) for cross-camera identity matching via FAISS. Does not produce anomaly scores.

### Import pattern

Detector wrappers in `pipeline/detectors/` add the `ai/` directory to `sys.path` at runtime so they can import from `components.*`. This is necessary because there is no `setup.py` / `pyproject.toml`.

### Model weights

Checkpoints live in `ai/weights/`:
- `crime_skelnet/best_anomaly_skel.pth`
- `video_mae/best_model_higher_94.pth`
- `weapon_detection/best.pt`
- `ai/yolov8x-pose.pt` (pose model, at ai/ root)

Additional models are downloaded at runtime from HuggingFace (VideoMAE-Large, Swin gunshot) and TF Hub (YAMNet).

### Relationship to backend

The AI pipeline is currently standalone. It will eventually be wrapped as an AI service that pushes detections to the backend via:
- `POST /api/v1/edge/sync` — batch detection payload (creates incidents in `detecting` status)
- `POST /api/v1/edge/classify` — upgrades detections to confirmed incidents, triggers Kafka events

See `backend/CLAUDE.md` for the full backend architecture.
