import sys
from pathlib import Path

import torch
import tensorflow_hub as hub
from transformers import pipeline, AutoImageProcessor

from ..config import Config


class PAANModels:
    """Loads and holds the three inference models used by the PAAN pipeline."""

    def __init__(self, cfg: Config | None = None):
        if cfg is None:
            cfg = Config()

        device = cfg.device if torch.cuda.is_available() else "cpu"

        # Stage 1: YAMNet
        self.yamnet = hub.load(cfg.yamnet_url)

        # Stage 2: Swin Gunshot Classifier
        image_processor = AutoImageProcessor.from_pretrained(cfg.gunshot_model)
        self.gunshot_classifier = pipeline(
            "image-classification",
            model=cfg.gunshot_model,
            image_processor=image_processor,
        )

        # Stage 3: FlexSED
        flexsed_dir = Path(__file__).resolve().parent.parent / "FlexSED"
        if str(flexsed_dir) not in sys.path:
            sys.path.insert(0, str(flexsed_dir))

        from api import FlexSED
        self.flexsed = FlexSED(device=device)

        self.device = device


__all__ = ["PAANModels"]
