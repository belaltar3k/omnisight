"""Identity Fusion Manager: coordinates feature extraction and database queries."""

from typing import Optional

import numpy as np

from ..config import Config
from .feature_extractor import FeatureExtractorEngine
from .database import DatabaseManager


class IdentityFusionManager:
    """
    Maintains Active Track Memory and coordinates feature extraction
    and database queries to resolve Global IDs across cameras.
    """

    def __init__(
        self,
        feature_engine: FeatureExtractorEngine,
        db_manager: DatabaseManager,
        cfg: Config | None = None,
    ) -> None:
        if cfg is None:
            cfg = Config()
        self.cfg = cfg
        self.feature_engine = feature_engine
        self.db_manager = db_manager
        self.active_memory: dict[tuple[str, int], int] = {}
        self._frame_counter: dict[tuple[str, int], int] = {}

    def resolve_identity(
        self, camera_id: str, local_track_id: int, crop_img: np.ndarray
    ) -> int:
        key = (camera_id, local_track_id)

        if key in self.active_memory:
            self._frame_counter[key] = self._frame_counter.get(key, 0) + 1
            if self._frame_counter[key] % self.cfg.recheck_interval == 0:
                clothes_emb = self.feature_engine._extract_appearance(crop_img)
                self.db_manager.add_appearance_vector(self.active_memory[key], clothes_emb)
            return self.active_memory[key]

        features = self.feature_engine.extract_features(crop_img)
        face_emb = features["face_emb"]
        clothes_emb = features["clothes_emb"]

        global_id: Optional[int] = None

        if face_emb is not None:
            global_id, _ = self.db_manager.search_face(face_emb)
            if global_id is not None:
                self.db_manager.add_appearance_vector(global_id, clothes_emb)

        if global_id is None:
            global_id, _ = self.db_manager.search_appearance(clothes_emb)
            if global_id is not None:
                self.db_manager.add_appearance_vector(global_id, clothes_emb)

        if global_id is None:
            global_id = self.db_manager.register_new_person(
                face_emb, clothes_emb, camera_id, local_track_id
            )

        self.db_manager.update_last_seen(global_id, camera_id)
        self.active_memory[key] = global_id
        self._frame_counter[key] = 0
        return global_id

    def cleanup_stale_tracks(self, camera_id: str, active_track_ids: set[int]) -> None:
        stale_keys = [
            key for key in self.active_memory
            if key[0] == camera_id and key[1] not in active_track_ids
        ]
        for key in stale_keys:
            del self.active_memory[key]
            self._frame_counter.pop(key, None)
