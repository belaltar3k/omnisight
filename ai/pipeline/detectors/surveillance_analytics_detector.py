from __future__ import annotations

import os
from typing import Optional

import numpy as np

from pipeline.base import BaseDetector, DetectorResult
from pipeline.config import PipelineConfig


class SurveillanceAnalyticsDetector(BaseDetector):
    name: str = "surveillance_analytics"
    modality: str = "video"

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def load(self, device: str) -> None:
        # Loading is handled during predict via VideoEngine initialization
        pass

    def predict(self, video_path: str, **kwargs) -> Optional[DetectorResult]:
        from surveillance_analytics.config import SmartCityConfig
        from surveillance_analytics.core.engine import VideoEngine
        
        total_frames = kwargs.get("total_frames", 30)

        config = SmartCityConfig(
            video_source=video_path,
            device="cuda", # Defaulting to cuda for simplicity
            output_dir=self.output_dir,
            save_output_video=False, # We don't need its own output video since pipeline does it
        )
        
        # Monkey patch cv2.imshow to prevent it from popping up windows if we don't want to
        import cv2
        original_imshow = cv2.imshow
        cv2.imshow = lambda *a, **kw: None
        original_waitKey = cv2.waitKey
        cv2.waitKey = lambda *a, **kw: 1

        try:
            engine = VideoEngine(config)
            engine.run()
            
            # Extract base stats
            stats = {
                "persons": len(engine.tracker.get_persons()),
                "vehicles": len(engine.tracker.get_vehicles()),
                "total_alerts": len(engine.alert_system.get_recent(1000)),
            }
            
            # Extract detailed module stats
            if hasattr(engine, "_module_results"):
                for mod_name, mod_data in engine._module_results.items():
                    if isinstance(mod_data, dict):
                        for k, v in mod_data.items():
                            # Skip long series data to avoid flooding JSON/terminal
                            if isinstance(v, list) and len(v) > 5 and isinstance(v[0], dict):
                                continue
                            stats[f"{mod_name}_{k}"] = v
                    else:
                        stats[mod_name] = str(mod_data)
        finally:
            cv2.imshow = original_imshow
            cv2.waitKey = original_waitKey

        # We return 0.0 scores so it doesn't affect the anomaly threshold
        scores = np.zeros(total_frames, dtype=np.float32)

        return DetectorResult(
            scores=scores,
            num_frames=total_frames,
            metadata={"stats": stats}
        )
