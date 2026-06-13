# MTMCT — Multi-Target Multi-Camera Tracking

Real-time person tracking system that assigns persistent **Global IDs** across multiple camera streams by fusing three signals:

1. **Per-camera tracking** — YOLOv8 + ByteTrack assigns local track IDs per camera
2. **Face recognition** — InsightFace (`buffalo_l`) produces 512-D face embeddings
3. **Appearance Re-ID** — OSNet (`osnet_x1_0`) produces 512-D body/clothing embeddings

Embeddings are matched against a FAISS vector database to resolve globally consistent identities.

## Project Structure

```
tracking/
├── config/
│   ├── __init__.py
│   └── settings.py          # All configuration (thresholds, model paths, etc.)
├── models/
│   ├── __init__.py
│   ├── feature_extractor.py # InsightFace + OSNet embedding extraction
│   ├── database.py          # FAISS indices + SQLite identity store
│   ├── fusion.py            # Identity resolution decision tree
│   ├── filters.py           # Anti-furniture filters + temporal gating
│   └── streamer.py          # Multi-camera threaded frame reader
├── inference/
│   ├── __init__.py
│   └── video_inference.py   # Main MTMCT pipeline + CLI
├── scripts/
│   ├── setup.py             # Download models + install deps
│   └── run_tracking.py      # Convenience run script
├── README.md
└── requirements.txt
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup (downloads YOLO weights, checks GPU)
python scripts/setup.py

# 3. Run inference
python scripts/run_tracking.py --videos cam1.mp4 cam2.mp4
```

## Usage

### As a script
```bash
python scripts/run_tracking.py --videos video1.mp4 video2.mp4 --yolo-model yolov8m.pt
```

### As a module
```bash
python -m ai.components.tracking.inference.video_inference --videos cam1.mp4
```

### Programmatic
```python
from ai.components.tracking.config import Config
from ai.components.tracking.inference import run_inference

cfg = Config()
cfg.yolo_model = "yolov8m.pt"
cfg.face_threshold = 0.45

run_inference(["cam1.mp4", "cam2.mp4"], cfg)
```

## Configuration

All settings are in `config/settings.py` as a dataclass. Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `yolo_model` | `yolov8s.pt` | YOLO model weights path |
| `yolo_conf` | `0.8` | Detection confidence threshold |
| `face_threshold` | `0.40` | Minimum cosine similarity for face match |
| `appearance_threshold` | `0.55` | Minimum cosine similarity for appearance match |
| `n_confirm_frames` | `4` | Frames before a track is confirmed as a person |
| `min_aspect_ratio` | `1.4` | Height/width ratio filter (rejects furniture) |

## Architecture

See `MTMCT_Architecture.md` for the full system design document with mermaid diagrams.

## Anti-Furniture Filtering

The system includes a multi-layer filtering pipeline to reject false-positive detections (chairs, furniture):

1. **Geometry + luminance** — area, aspect ratio, pixel height, vertical luminance variance
2. **Clothing color variance** — HSV saturation check on torso region
3. **Temporal consistency** — track must survive N consecutive frames before registration
