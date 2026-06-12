# CrimeSkelNet

5-stream Graph Convolutional Network for real-time skeleton-based
anomaly detection. Achieves **0.98 Recall** on the unified multiple datasets
benchmark.

## Quickstart

```bash
# 1. Build unified dataset (run on AWS, datasets must be in /data/datasets)
python scripts/build_dataset.py

# 2. Train
python scripts/train.py

# 3. Infer on a single video
python inference/video_inference.py \
    --video test.mp4 \
    --weights /data/checkpoints/best_anomaly_skel.pth \
    --output  result.mp4
```

## Architecture

| Stream | Feature | Shape |
|--------|---------|-------|
| 0 | Joint coordinates | (3, T, 17, M) |
| 1 | Bone vectors | (3, T, 17, M) |
| 2 | Joint motion (velocity) | (3, T, 17, M) |
| 3 | Bone motion | (3, T, 17, M) |
| 4 | Bone angles | (3, T, 17, M) |