from __future__ import annotations

import os
import subprocess
import time
import traceback

import cv2
import numpy as np

from .base import BaseDetector, DetectorResult
from .config import PipelineConfig
from .fusion import WeightedFusionEngine
from .result import PipelineResult


def _default_registry() -> dict[str, callable]:
    from .detectors import VideoMAEDetector, SkelNetDetector, PAANDetector, WeaponDetector, SurveillanceAnalyticsDetector

    return {
        "crime_skelnet": lambda cfg: SkelNetDetector(cfg.skelnet_weights, cfg.pose_model),
        "weapon_detection": lambda cfg: WeaponDetector(cfg.weapon_weights, cfg.weapon_sample_fps),
        "video_mae": lambda cfg: VideoMAEDetector(cfg.video_mae_weights),
        "paan": lambda cfg: PAANDetector(),
        "surveillance_analytics": lambda cfg: SurveillanceAnalyticsDetector(cfg.output_dir if hasattr(cfg, 'output_dir') else "pipeline_output"),
    }


class PipelineRunner:

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.fusion = WeightedFusionEngine(
            weights=config.weights,
            anomaly_threshold=config.anomaly_threshold,
            smoothing_window=config.smoothing_window,
            dominance_weight=config.dominance_weight,
        )

    @staticmethod
    def _free_memory() -> None:
        import gc
        gc.collect()
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
        except (ImportError, RuntimeError):
            pass
        gc.collect()

    @staticmethod
    def _video_has_audio(video_path: str) -> bool:
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-select_streams", "a",
                    "-show_entries", "stream=codec_type",
                    "-of", "csv=p=0",
                    video_path,
                ],
                capture_output=True, text=True, timeout=10,
            )
            return "audio" in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            from moviepy import VideoFileClip
            clip = VideoFileClip(video_path)
            has = clip.audio is not None
            clip.close()
            return has
        except Exception:
            pass

        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(video_path)
            return len(audio) > 0
        except Exception:
            pass

        print("[Pipeline] WARN — cannot detect audio (install ffprobe, moviepy, or pydub). Assuming audio exists.")
        return True

    def run(self, video_path: str) -> PipelineResult:
        t_start = time.time()

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        print(f"[Pipeline] Video: {video_path}  |  {total_frames} frames @ {fps:.1f} FPS "
              f"({total_frames / fps:.1f}s)")

        registry = _default_registry()
        disabled = set(self.config.disabled)
        failed: dict[str, str] = {}

        has_audio = self._video_has_audio(video_path)
        if has_audio:
            print("[Pipeline] Audio track detected — PAAN enabled.")
        elif "paan" not in disabled:
            print("[Pipeline] No audio track detected — skipping PAAN.")
            disabled.add("paan")

        results: dict[str, DetectorResult] = {}
        for name, factory in registry.items():
            if name in disabled:
                continue
            weight = self.config.weights.get(name, 0)
            if weight <= 0 and name != "surveillance_analytics":
                continue

            try:
                det = factory(self.config)
            except Exception as exc:
                failed[name] = f"build error: {exc}"
                print(f"[Pipeline] WARN — failed to build {name}: {exc}")
                continue

            try:
                self._free_memory()
                print(f"\n[Pipeline] Loading {det.name}...")
                det.load(self.config.device)
            except Exception as exc:
                failed[det.name] = f"load error: {exc}"
                print(f"[Pipeline] WARN — failed to load {det.name}: {exc}")
                traceback.print_exc()
                continue

            try:
                print(f"[Pipeline] Running {det.name}...")
                t0 = time.time()
                result = det.predict(video_path, total_frames=total_frames)
                elapsed = time.time() - t0
                if result is not None:
                    results[det.name] = result
                    peak = float(result.scores.max()) if len(result.scores) > 0 else 0.0
                    print(f"[Pipeline] {det.name} done in {elapsed:.1f}s  "
                          f"(peak={peak:.3f}, frames={len(result.scores)})")
                else:
                    print(f"[Pipeline] {det.name} returned None (skipped) in {elapsed:.1f}s")
            except Exception as exc:
                failed[det.name] = f"predict error: {exc}"
                print(f"[Pipeline] WARN — {det.name} failed during predict: {exc}")
                traceback.print_exc()
            finally:
                del det
                self._free_memory()

        processing_time = time.time() - t_start

        pipeline_result = self.fusion.fuse(
            results,
            num_frames=total_frames,
            fps=fps,
            processing_time=processing_time,
            failed_components=failed,
            disabled_components=list(disabled),
        )

        print(f"\n[Pipeline] Fusion complete in {processing_time:.1f}s  "
              f"|  peak={pipeline_result.peak_score:.3f}  "
              f"|  anomalous={pipeline_result.is_anomalous}  "
              f"|  regions={len(pipeline_result.anomaly_regions)}")

        return pipeline_result
