"""
PAAN (Pipeline for Audio ANomaly detection) inference.

Three-stage audio surveillance pipeline:
    1. YAMNet — coarse filtering for crime-related sound classes.
    2. Swin Gunshot Classifier — verifies ballistic signatures via spectrogram.
    3. FlexSED — semantic reasoning over descriptive surveillance events.

Usage:
    python inference/run_paan.py --audio /path/to/file.wav
    python inference/run_paan.py --audio clip.mp3 --gunshot-thresh 0.8
"""

import argparse
import csv
import os
import sys
import time

# Add the project root to sys.path so relative imports work when run as a script
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

__package__ = "ai.components.paan.inference"

import numpy as np
import torch
import torch.nn.functional as F
import torchaudio
import librosa
import soundfile as sf
import scipy.signal
import tensorflow as tf
from PIL import Image

from ..config import Config
from ..models import PAANModels


# -- Preprocessing utilities --------------------------------------------------

def _yamnet_class_names(yamnet_model) -> list[str]:
    class_names = []
    with tf.io.gfile.GFile(yamnet_model.class_map_path().numpy()) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            class_names.append(row["display_name"])
    return class_names


def _preprocess_wav_to_spectrogram(file_path: str, cfg: Config) -> Image.Image:
    """Generate a 224x224 log-mel spectrogram PIL image for the Swin model."""
    waveform, orig_sr = torchaudio.load(file_path)

    # Convert stereo (or any multi-channel) to mono
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)  # (1, T)

    if orig_sr != cfg.gunshot_sr:
        resampler = torchaudio.transforms.Resample(orig_sr, cfg.gunshot_sr)
        waveform = resampler(waveform)

    target_samples = int(cfg.gunshot_clip_s * cfg.gunshot_sr)
    if waveform.shape[1] > target_samples:
        waveform = waveform[:, :target_samples]
    else:
        padding = target_samples - waveform.shape[1]
        waveform = F.pad(waveform, (0, padding))

    mel_spec = torchaudio.transforms.MelSpectrogram(
        sample_rate=cfg.gunshot_sr,
        n_fft=cfg.n_fft,
        hop_length=cfg.hop_length,
        n_mels=cfg.n_mels,
        power=1.0,
    )(waveform)  # shape: (1, n_mels, T)

    log_spec = torchaudio.transforms.AmplitudeToDB()(mel_spec)  # (1, n_mels, T)
    log_spec = (log_spec + 80) / 80
    log_spec = log_spec.repeat(3, 1, 1)  # (3, n_mels, T)
    log_spec = F.interpolate(
        log_spec.unsqueeze(0), size=(224, 224), mode="bilinear", align_corners=False
    ).squeeze(0)  # (3, 224, 224)

    log_spec_np = log_spec.permute(1, 2, 0).detach().numpy()  # (224, 224, 3)
    log_spec_np = np.clip(log_spec_np * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(log_spec_np, mode="RGB")


# -- Main inference pipeline --------------------------------------------------

def run_inference(
    audio_path: str,
    cfg: Config | None = None,
    models: PAANModels | None = None,
) -> dict:
    """
    Run the full PAAN 3-stage pipeline on an audio file.

    Returns a dict with keys:
        yamnet_candidates: list of (class_name, score) tuples
        gunshot_verified:  bool or None (None if stage 2 was skipped)
        flexsed_results:   list of (event_description, score) tuples
        total_time:        float seconds
    """
    if cfg is None:
        cfg = Config()
    if models is None:
        models = PAANModels(cfg)

    total_start = time.time()

    # ── Stage 1: YAMNet ─────────────────────────────────────────────────────
    print("[STAGE 1] YAMNet (coarse filtering)...")
    wav_data, _ = librosa.load(audio_path, sr=cfg.sample_rate, mono=True)
    waveform = wav_data.astype(np.float32)

    scores, _, _ = models.yamnet(waveform)
    mean_scores = np.mean(scores.numpy(), axis=0)

    yamnet_classes = _yamnet_class_names(models.yamnet)
    yamnet_candidates = []
    needs_gunshot_verify = False

    for i, score in enumerate(mean_scores):
        name = yamnet_classes[i]
        if any(kw in name.lower() for kw in cfg.crime_keywords) and score > cfg.yamnet_thresh:
            yamnet_candidates.append((name, float(score)))
            if "gun" in name.lower() or "explosion" in name.lower():
                needs_gunshot_verify = True

    if not yamnet_candidates:
        print("  No suspicious sounds detected.")
        return {
            "yamnet_candidates": [],
            "gunshot_verified": None,
            "flexsed_results": [],
            "total_time": time.time() - total_start,
        }

    for name, score in yamnet_candidates[:5]:
        print(f"  Detected: {name:<20} | Confidence: {score:.4f}")

    # ── Stage 2: Gunshot classifier ─────────────────────────────────────────
    gunshot_verified = None
    if needs_gunshot_verify:
        print("[STAGE 2] Swin Gunshot Classifier (verification)...")
        spec_img = _preprocess_wav_to_spectrogram(audio_path, cfg)
        gunshot_results = models.gunshot_classifier(spec_img)

        gunshot_verified = any(
            res["label"].lower() == "gunshot" and res["score"] > cfg.gunshot_thresh
            for res in gunshot_results
        )
        print(f"  Gunshot {'VERIFIED' if gunshot_verified else 'not confirmed'}.")
    else:
        print("[STAGE 2] Skipped (no ballistic signatures in Stage 1).")

    # ── Stage 3: FlexSED ────────────────────────────────────────────────────
    print("[STAGE 3] FlexSED (semantic reasoning)...")
    audio, _ = librosa.load(audio_path, sr=cfg.sample_rate, mono=True)
    audio = librosa.util.normalize(audio)

    temp_wav = os.path.join(os.path.dirname(audio_path) or ".", "_paan_temp.wav")
    sf.write(temp_wav, audio, cfg.sample_rate)

    all_preds = []
    with torch.no_grad():
        for i in range(0, len(cfg.surveillance_events), cfg.flexsed_batch):
            chunk = cfg.surveillance_events[i : i + cfg.flexsed_batch]
            preds_chunk = models.flexsed.run_inference(temp_wav, chunk, norm_audio=True)
            all_preds.append(preds_chunk)

    preds = torch.cat(all_preds, dim=0)
    scores_max = preds[:, 0].max(dim=1).values.cpu().numpy()

    flexsed_results = [
        (evt, float(sc))
        for evt, sc in zip(cfg.surveillance_events, scores_max)
        if sc > cfg.flexsed_thresh
    ]
    flexsed_results.sort(key=lambda x: x[1], reverse=True)

    if os.path.exists(temp_wav):
        os.remove(temp_wav)

    total_time = time.time() - total_start

    if flexsed_results:
        print("RESULTS:")
        for event, score in flexsed_results:
            print(f"  [ALERT] {event} -> Confidence: {score:.4f}")
    else:
        print("  No high-confidence semantic matches.")

    print(f"Total pipeline time: {total_time:.3f}s")

    return {
        "yamnet_candidates": yamnet_candidates,
        "gunshot_verified": gunshot_verified,
        "flexsed_results": flexsed_results,
        "total_time": total_time,
    }


# -- CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run PAAN audio surveillance inference.")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--yamnet-thresh", type=float, default=None)
    parser.add_argument("--gunshot-thresh", type=float, default=None)
    parser.add_argument("--flexsed-thresh", type=float, default=None)
    args = parser.parse_args()

    cfg = Config()
    if args.yamnet_thresh is not None:
        cfg.yamnet_thresh = args.yamnet_thresh
    if args.gunshot_thresh is not None:
        cfg.gunshot_thresh = args.gunshot_thresh
    if args.flexsed_thresh is not None:
        cfg.flexsed_thresh = args.flexsed_thresh

    run_inference(args.audio, cfg)