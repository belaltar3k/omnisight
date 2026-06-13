"""Feature extraction engine: InsightFace (face) + OSNet (appearance Re-ID)."""

from typing import Optional

import cv2
import numpy as np
import torch
from insightface.app import FaceAnalysis
from torchreid.utils import FeatureExtractor

from ..config import Config


class FeatureExtractorEngine:
    """Extracts face embeddings (InsightFace) and appearance embeddings (OSNet)."""

    def __init__(self, cfg: Config | None = None) -> None:
        if cfg is None:
            cfg = Config()

        device = cfg.device if torch.cuda.is_available() else "cpu"

        self.face_model = FaceAnalysis(
            name=cfg.face_model_name,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.face_model.prepare(ctx_id=0, det_size=cfg.face_det_size)

        self.reid_model = FeatureExtractor(
            model_name=cfg.reid_model_name,
            model_path="",
            device=device,
        )

        self.reid_input_size = cfg.reid_input_size

    def extract_features(self, crop_img: np.ndarray) -> dict:
        """
        Extract face and appearance embeddings from a person crop.

        Returns dict with keys:
            "face_emb": np.ndarray (512,) or None if no face detected
            "clothes_emb": np.ndarray (512,) L2-normalized appearance vector
        """
        face_emb = self._extract_face(crop_img)
        clothes_emb = self._extract_appearance(crop_img)
        return {"face_emb": face_emb, "clothes_emb": clothes_emb}

    def _extract_face(self, crop_img: np.ndarray) -> Optional[np.ndarray]:
        faces = self.face_model.get(crop_img)
        if not faces:
            return None
        embedding = faces[0].embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.astype(np.float32)

    def _extract_appearance(self, crop_img: np.ndarray) -> np.ndarray:
        img_rgb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, self.reid_input_size)
        img_tensor = img_resized.transpose(2, 0, 1).astype(np.float32) / 255.0
        img_tensor = np.expand_dims(img_tensor, axis=0)
        img_tensor = torch.from_numpy(img_tensor)

        with torch.no_grad():
            features = self.reid_model(img_tensor)

        embedding = features.cpu().numpy().flatten().astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding
