from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Optional

import numpy as np

from ..base import BaseDetector, DetectorResult


class PAANDetector(BaseDetector):
    name = "paan"
    modality = "audio"

    def __init__(self) -> None:
        self.device = "cpu"
        self.models = None
        self.cfg = None

    def load(self, device: str) -> None:
        import sys
        comp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        if comp_root not in sys.path:
            sys.path.insert(0, comp_root)

        flexsed_dir = os.path.join(comp_root, "components", "paan", "FlexSED")
        if not os.path.isdir(flexsed_dir):
            raise RuntimeError(
                "FlexSED not found — run: python components/paan/scripts/setup_flexsed.py"
            )

        from components.paan.config import Config
        from components.paan.models import PAANModels

        self.device = device
        self.cfg = Config()
        self.cfg.device = device

        print("[PAAN] Loading models (YAMNet + Swin + FlexSED)...")
        self.models = PAANModels(self.cfg)

    @staticmethod
    def _has_audio(video_path: str) -> bool:
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
            return True

    @staticmethod
    def _extract_audio(video_path: str, output_path: str) -> bool:
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", video_path,
                    "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                    output_path,
                ],
                capture_output=True, timeout=120,
            )
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            from moviepy import VideoFileClip, AudioFileClip
            clip = VideoFileClip(video_path)
            if clip.audio is None:
                clip.close()
                return False
            clip.audio.write_audiofile(
                output_path, fps=16000, nbytes=2,
                codec="pcm_s16le", logger=None,
            )
            clip.close()
            return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
        except Exception:
            return False

    def predict(self, video_path: str, **kwargs) -> Optional[DetectorResult]:
        total_frames = kwargs.get("total_frames", 0)

        if not self._has_audio(video_path):
            print("[PAAN] No audio track found — skipping.")
            return None

        tmp_dir = tempfile.mkdtemp(prefix="paan_")
        audio_path = os.path.join(tmp_dir, "audio.wav")

        if not self._extract_audio(video_path, audio_path):
            print("[PAAN] Failed to extract audio — skipping.")
            return None

        import sys
        comp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        if comp_root not in sys.path:
            sys.path.insert(0, comp_root)
        from components.paan.inference.run_paan import run_inference as paan_run

        print("[PAAN] Running 3-stage audio analysis...")
        result = paan_run(audio_path, self.cfg, self.models)

        os.remove(audio_path)
        os.rmdir(tmp_dir)

        yamnet_score = max((s for _, s in result["yamnet_candidates"]), default=0.0)
        flexsed_score = max((s for _, s in result["flexsed_results"]), default=0.0)

        combined_score = max(yamnet_score, flexsed_score)

        if result["gunshot_verified"]:
            combined_score = max(combined_score, 0.9)

        if total_frames > 0:
            scores = np.full(total_frames, combined_score, dtype=np.float32)
        else:
            scores = np.array([combined_score], dtype=np.float32)

        return DetectorResult(
            scores=scores,
            num_frames=total_frames,
            metadata={
                "yamnet_candidates": result["yamnet_candidates"],
                "gunshot_verified": result["gunshot_verified"],
                "flexsed_results": result["flexsed_results"],
            },
        )
