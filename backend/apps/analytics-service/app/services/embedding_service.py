"""
Singleton embedding service using fastembed (ONNX, no torch needed).
Model: BAAI/bge-small-en-v1.5  — 384 dims, fast CPU inference.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed import TextEmbedding
                logger.info("Loading fastembed model BAAI/bge-small-en-v1.5 ...")
                _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
                logger.info("Embedding model loaded.")
    return _model


def embed_text(text: str) -> list[float]:
    """Return a 384-dim embedding vector for the given text."""
    model = _get_model()
    vectors = list(model.embed([text]))
    return vectors[0].tolist()


def build_vlm_text(caption: str, events: list, crime_type: str, zone: str = "") -> str:
    """Construct the text we embed for each VLM analysis record."""
    parts = []
    if caption:
        parts.append(caption)
    if events:
        parts.append("Events: " + "; ".join(str(e) for e in events[:5]))
    if crime_type and crime_type != "abnormal":
        parts.append(f"Crime type: {crime_type}")
    if zone:
        parts.append(f"Zone: {zone}")
    return ". ".join(parts) if parts else "no description"


def embed_and_store(row, db) -> None:
    """
    Compute embedding for a VLM analysis row and persist it.
    Designed to be called from a background thread so it never blocks ingest.
    """
    try:
        text = build_vlm_text(
            caption=row.caption or "",
            events=row.events or [],
            crime_type=row.crime_type or "",
            zone=row.zone or "",
        )
        vec = embed_text(text)
        from sqlalchemy import text as sql_text
        db.execute(
            sql_text(
                "UPDATE vlm_analyses SET embedding = :emb WHERE id = :id AND timestamp = :ts"
            ),
            {"emb": str(vec), "id": str(row.id), "ts": row.timestamp},
        )
        db.commit()
        logger.debug("Embedding stored for vlm_analysis id=%s", row.id)
    except Exception as e:
        logger.warning("embed_and_store failed for id=%s: %s", row.id, e)
