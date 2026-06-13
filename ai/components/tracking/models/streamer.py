"""Multi-camera frame reader with threaded capture."""

import queue
import threading

import cv2
import numpy as np


class MultiCameraStreamer:
    """Reads frames from multiple video sources using dedicated threads."""

    def __init__(self, sources: list[str]) -> None:
        self.sources = sources
        self.queues: dict[str, queue.Queue] = {}
        self.threads: list[threading.Thread] = []
        self.running = True

        for i, source in enumerate(sources):
            camera_id = f"cam_{i}"
            q = queue.Queue(maxsize=2)
            self.queues[camera_id] = q
            t = threading.Thread(
                target=self._reader, args=(source, camera_id, q), daemon=True
            )
            t.start()
            self.threads.append(t)

    def _reader(self, source: str, camera_id: str, q: queue.Queue) -> None:
        cap = cv2.VideoCapture(source)
        while self.running:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            if not q.full():
                try:
                    q.put_nowait(frame)
                except queue.Full:
                    pass
            else:
                try:
                    q.get_nowait()
                    q.put_nowait(frame)
                except (queue.Empty, queue.Full):
                    pass
        cap.release()

    def get_frames(self) -> list[tuple[str, np.ndarray]]:
        frames = []
        for camera_id, q in self.queues.items():
            try:
                frame = q.get_nowait()
                frames.append((camera_id, frame))
            except queue.Empty:
                pass
        return frames

    def stop(self) -> None:
        self.running = False
        for t in self.threads:
            t.join(timeout=2)
