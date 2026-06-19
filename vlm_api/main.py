"""
Omnisight VLM Service — Qwen2.5-VL-7B-Instruct via vLLM
Receives anomaly frames from ai-detection, returns structured crime analysis.
"""
from __future__ import annotations

import base64
import json
import logging
import time
import uuid
from io import BytesIO
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from PIL import Image
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# vLLM serves the model at localhost:8000 with the OpenAI-compatible API
VLLM_BASE_URL = "http://localhost:8000/v1"
MODEL_NAME = "Qwen/Qwen2.5-VL-7B-Instruct"  # overridden at startup by auto-discovery
MAX_FRAMES = 4  # this Qwen deployment allows at most 5 images per prompt


def _discover_model() -> str:
    """Query vLLM /v1/models and return the first available model id."""
    import urllib.request as _ur
    try:
        with _ur.urlopen("http://localhost:8000/v1/models", timeout=10) as r:
            data = json.loads(r.read())
            models = data.get("data", [])
            if models:
                name = models[0]["id"]
                logger.info("Auto-discovered vLLM model: %s", name)
                return name
    except Exception as e:
        logger.warning("Model discovery failed, using default: %s", e)
    return MODEL_NAME

CRIME_TYPES = [
    "assault", "theft", "shoplifting", "vandalism",
    "fire", "weapon", "intrusion", "accident", "suspicious", "normal"
]

ANALYSIS_PROMPT = """You are a surveillance AI expert. Analyze the provided security camera frames and respond ONLY with a valid JSON object — no markdown, no explanation.

Use this exact schema:
{
  "crime_type": "<one of: assault, theft, shoplifting, vandalism, fire, weapon, intrusion, accident, suspicious, normal>",
  "anomaly_score_vlm": "<LOW|MEDIUM|HIGH>",
  "people_count": <integer>,
  "observed_events": ["<concise event description>"],
  "anomaly_evidence": ["<specific visual evidence that supports the crime_type>"],
  "caption": "<one sentence describing what is happening in the scene>"
}

Rules:
- crime_type must be exactly one value from the list above
- anomaly_score_vlm: HIGH if violent/dangerous activity, MEDIUM if suspicious, LOW if uncertain
- people_count: count visible people across all frames
- observed_events: 1-5 specific actions observed
- anomaly_evidence: 1-5 pieces of visual evidence justifying the crime_type
- caption: a clear, factual one-sentence summary
"""

app = FastAPI(title="Omnisight VLM Service", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(base_url=VLLM_BASE_URL, api_key="EMPTY")


@app.on_event("startup")
def on_startup():
    global MODEL_NAME
    MODEL_NAME = _discover_model()
    logger.info("VLM service ready — model=%s port=8001", MODEL_NAME)


class AnalyzeRequest(BaseModel):
    event_id: Optional[str] = None
    camera_id: str
    zone: str = ""
    anomaly_score_fusion: float = 0.0
    frames: List[str]           # base64-encoded JPEG frames
    video_url: Optional[str] = None


class AnalyzeResponse(BaseModel):
    event_id: str
    timestamp: str
    camera_id: str
    zone: str
    anomaly_score_fusion: float
    crime_type: str
    anomaly_score_vlm: str
    people_count: int
    observed_events: List[str]
    anomaly_evidence: List[str]
    caption: str
    video_url: Optional[str]
    raw_vlm_output: str


def _resize_frame(b64_jpeg: str, max_dim: int = 512) -> str:
    """Resize frame to reduce token usage while keeping aspect ratio."""
    try:
        img_bytes = base64.b64decode(b64_jpeg)
        img = Image.open(BytesIO(img_bytes))
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return b64_jpeg


def _sample_frames(frames: List[str], n: int) -> List[str]:
    if len(frames) <= n:
        return frames
    indices = [int(i * (len(frames) - 1) / (n - 1)) for i in range(n)]
    return [frames[i] for i in indices]


def _call_qwen(frames: List[str]) -> str:
    """Call Qwen2.5-VL via vLLM OpenAI-compatible API."""
    content = [{"type": "text", "text": ANALYSIS_PROMPT}]
    for b64 in frames:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": content}],
        max_tokens=512,
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


def _parse_vlm_output(raw: str) -> dict:
    """Extract JSON from VLM output, with fallback defaults."""
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract the first JSON object from the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                parsed = json.loads(text[start:end])
            except json.JSONDecodeError:
                parsed = {}
        else:
            parsed = {}

    crime_type = parsed.get("crime_type", "suspicious")
    if crime_type not in CRIME_TYPES:
        crime_type = "suspicious"

    vlm_score = parsed.get("anomaly_score_vlm", "MEDIUM")
    if vlm_score not in ("LOW", "MEDIUM", "HIGH"):
        vlm_score = "MEDIUM"

    return {
        "crime_type": crime_type,
        "anomaly_score_vlm": vlm_score,
        "people_count": int(parsed.get("people_count", 0)),
        "observed_events": parsed.get("observed_events", []),
        "anomaly_evidence": parsed.get("anomaly_evidence", []),
        "caption": parsed.get("caption", ""),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    event_id = req.event_id or str(uuid.uuid4())
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if not req.frames:
        raise HTTPException(status_code=400, detail="No frames provided")

    # Sample and resize frames to stay within context
    sampled = _sample_frames(req.frames, MAX_FRAMES)
    resized = [_resize_frame(f) for f in sampled]

    logger.info(
        "VLM analyze: event=%s camera=%s frames_in=%d frames_used=%d",
        event_id, req.camera_id, len(req.frames), len(resized),
    )

    t0 = time.time()
    try:
        raw_output = _call_qwen(resized)
    except Exception as e:
        logger.error("Qwen call failed: %s", e)
        raise HTTPException(status_code=502, detail=f"VLM inference failed: {e}")

    elapsed = time.time() - t0
    logger.info("VLM inference took %.1fs for event=%s", elapsed, event_id)

    parsed = _parse_vlm_output(raw_output)
    logger.info("VLM result: crime=%s score=%s people=%d event=%s",
                parsed["crime_type"], parsed["anomaly_score_vlm"], parsed["people_count"], event_id)

    return AnalyzeResponse(
        event_id=event_id,
        timestamp=timestamp,
        camera_id=req.camera_id,
        zone=req.zone,
        anomaly_score_fusion=req.anomaly_score_fusion,
        crime_type=parsed["crime_type"],
        anomaly_score_vlm=parsed["anomaly_score_vlm"],
        people_count=parsed["people_count"],
        observed_events=parsed["observed_events"],
        anomaly_evidence=parsed["anomaly_evidence"],
        caption=parsed["caption"],
        video_url=req.video_url,
        raw_vlm_output=raw_output,
    )


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.get("/models")
def list_models():
    """Proxy to vLLM /v1/models — shows what's actually loaded."""
    import urllib.request as _ur
    try:
        with _ur.urlopen("http://localhost:8000/v1/models", timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
