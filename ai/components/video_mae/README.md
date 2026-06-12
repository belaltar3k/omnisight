# VideoMAE — CrimeTransformer

Appearance-context anomaly detector achieving **94.89% AUC** on UCF-Crime,  
beating SOTA academic baselines.

---

## Architecture

```text
VideoMAE-Large (frozen)
        ↓
1024-D clip embeddings
        ↓
MultiScaleTemporalConv
(parallel Conv1D @ k=1,3,5)
        ↓
MagnitudeAttention
(RTFM-style magnitude gating)
        ↓
TransformerEncoder
(4-layer, 8-head, pre-norm)
       ↙             ↘
anomaly_head      class_head
(per-snippet)   (video-level, 14 classes)
```

---

## Quickstart

### Train

```bash
python scripts/train.py
```

### Infer on a Single Video

```bash
python inference/video_inference.py \
    --video   /path/to/video.mp4 \
    --weights /data/checkpoints/best_model.pth \
    --output  /data/output.png
```

---

## Results

| Metric      | Value   |
|-------------|----------|
| AUC-ROC     | 94.89%   |
| Best Epoch  | 20       |