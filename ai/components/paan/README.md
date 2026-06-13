# PAAN — Pipeline for Audio ANomaly Detection

Multi-stage audio surveillance component for the OmniSight system.
Detects gunshots, explosions, screaming, glass breaking, and other
crime-related audio events from microphone/CCTV audio feeds.

## Architecture

```
Audio Input
    │
    ▼
┌──────────────────────┐
│  Stage 1: YAMNet     │  Coarse filter — 521 sound classes
│  (TF Hub)            │  Passes if crime-keyword score > threshold
└──────────┬───────────┘
           │ candidates
           ▼
┌──────────────────────┐
│  Stage 2: Swin       │  Spectrogram → image classification
│  Gunshot Classifier  │  Confirms/rejects ballistic signatures
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Stage 3: FlexSED    │  Zero-shot semantic audio event detection
│  (Text-conditioned)  │  Scores descriptive surveillance queries
└──────────┬───────────┘
           │
           ▼
      Final Results
```

## Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Clone and install FlexSED
python scripts/setup_flexsed.py
```

## Inference

```bash
python inference/run_paan.py --audio /path/to/audio.wav

# With custom thresholds
python inference/run_paan.py --audio clip.mp3 \
    --yamnet-thresh 0.01 \
    --gunshot-thresh 0.8 \
    --flexsed-thresh 0.15
```

## Configuration

All pipeline parameters are defined in `config/settings.py` as a dataclass.
Override at runtime via CLI flags or by modifying the `Config` instance.
