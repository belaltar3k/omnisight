"""FAISS + SQLite database manager for person identity storage and retrieval."""

import threading
import sqlite3
from datetime import datetime
from typing import Optional

import numpy as np
import faiss

from ..config import Config


class DatabaseManager:
    """
    Manages FAISS indices for face/appearance vectors and SQLite for person metadata.
    """

    def __init__(self, cfg: Config | None = None) -> None:
        if cfg is None:
            cfg = Config()

        self.cfg = cfg
        self.lock = threading.Lock()

        self.conn = sqlite3.connect(cfg.db_path, check_same_thread=False)
        self._init_sqlite()

        self.face_index = faiss.IndexFlatIP(cfg.face_dim)
        self.appearance_index = faiss.IndexFlatIP(cfg.appearance_dim)

        self.face_id_map: list[int] = []
        self.appearance_id_map: list[int] = []

    def _init_sqlite(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                global_id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                last_camera TEXT
            )
        """)
        self.conn.commit()

    def register_new_person(
        self,
        face_emb: Optional[np.ndarray],
        clothes_emb: np.ndarray,
        camera_id: str,
        local_track_id: int = -1,
    ) -> int:
        with self.lock:
            now = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO persons (first_seen, last_seen, last_camera) VALUES (?, ?, ?)",
                (now, now, camera_id),
            )
            self.conn.commit()
            global_id = cursor.lastrowid

            if face_emb is not None:
                self.face_index.add(face_emb.reshape(1, -1))
                self.face_id_map.append(global_id)

            self.appearance_index.add(clothes_emb.reshape(1, -1))
            self.appearance_id_map.append(global_id)

        if self.cfg.debug_scores:
            print(
                f"[DEBUG] Registered NEW person -> global_id={global_id} "
                f"(camera={camera_id}, local_track_id={local_track_id})"
            )
        return global_id

    def search_face(self, face_emb: np.ndarray) -> tuple[Optional[int], float]:
        with self.lock:
            if self.face_index.ntotal == 0:
                return None, -1.0
            query = face_emb.reshape(1, -1)
            scores, indices = self.face_index.search(query, 1)
            best_score = float(scores[0][0])
            best_idx = int(indices[0][0])

        if self.cfg.debug_scores:
            print(f"[DEBUG] face best score = {best_score:.3f} (threshold = {self.cfg.face_threshold})")

        if best_score >= self.cfg.face_threshold:
            return self.face_id_map[best_idx], best_score
        return None, best_score

    def search_appearance(self, clothes_emb: np.ndarray) -> tuple[Optional[int], float]:
        with self.lock:
            n = self.appearance_index.ntotal
            if n == 0:
                return None, -1.0

            k = min(self.cfg.appearance_search_k, n)
            query = clothes_emb.reshape(1, -1)
            scores, indices = self.appearance_index.search(query, k)

            best_score = -1.0
            best_global_id: Optional[int] = None
            for score, idx in zip(scores[0], indices[0]):
                idx = int(idx)
                if idx < 0:
                    continue
                if float(score) > best_score:
                    best_score = float(score)
                    best_global_id = self.appearance_id_map[idx]

        if self.cfg.debug_scores:
            print(
                f"[DEBUG] appearance best score = {best_score:.3f} "
                f"(threshold = {self.cfg.appearance_threshold})"
            )

        if best_global_id is not None and best_score >= self.cfg.appearance_threshold:
            return best_global_id, best_score
        return None, best_score

    def add_appearance_vector(self, global_id: int, clothes_emb: np.ndarray) -> None:
        with self.lock:
            existing_rows = [
                i for i, gid in enumerate(self.appearance_id_map) if gid == global_id
            ]

            if len(existing_rows) >= self.cfg.max_appearance_vectors:
                drop_row = existing_rows[0]
                n = self.appearance_index.ntotal
                all_vectors = faiss.rev_swig_ptr(
                    self.appearance_index.get_xb(), n * self.cfg.appearance_dim
                ).reshape(n, self.cfg.appearance_dim).copy()

                all_vectors = np.delete(all_vectors, drop_row, axis=0)
                new_id_map = (
                    self.appearance_id_map[:drop_row]
                    + self.appearance_id_map[drop_row + 1:]
                )

                all_vectors = np.vstack([all_vectors, clothes_emb.reshape(1, -1)])
                new_id_map.append(global_id)

                self.appearance_index.reset()
                self.appearance_index.add(all_vectors)
                self.appearance_id_map = new_id_map
            else:
                self.appearance_index.add(clothes_emb.reshape(1, -1))
                self.appearance_id_map.append(global_id)

            now = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE persons SET last_seen = ? WHERE global_id = ?",
                (now, global_id),
            )
            self.conn.commit()

        if self.cfg.debug_scores:
            count = sum(1 for gid in self.appearance_id_map if gid == global_id)
            print(f"[DEBUG] global_id={global_id} appearance gallery size = {count}")

    def update_last_seen(self, global_id: int, camera_id: str) -> None:
        with self.lock:
            now = datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE persons SET last_seen = ?, last_camera = ? WHERE global_id = ?",
                (now, camera_id, global_id),
            )
            self.conn.commit()
