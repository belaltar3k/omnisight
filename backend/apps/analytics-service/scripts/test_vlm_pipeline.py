"""
End-to-end test of the VLM pipeline:
  1. VLM EC2 reachable + /health
  2. VLM /analyze with synthetic frames (actual Qwen inference)
  3. S3 clip upload
  4. analytics-service /vlm/ingest  (receives VLM result)
  5. analytics-service /vlm/analyses (query stored result)
  6. analytics-service /vlm/summary
  7. incident-service edge/classify  (simulate VLM reclassifying an incident)
"""
import base64
import json
import os
import struct
import time
import urllib.error
import urllib.request
import zlib

# ── Config ──────────────────────────────────────────────────────────────────
VLM_URL        = os.getenv("VLM_URL",        "http://ec2-13-60-2-232.eu-north-1.compute.amazonaws.com:8001")
ANALYTICS_URL  = os.getenv("ANALYTICS_URL",  "http://localhost:3006")
INCIDENT_URL   = os.getenv("INCIDENT_URL",   "http://localhost:3003")
GATEWAY_URL    = os.getenv("GATEWAY_URL",    "http://localhost:3000")
EDGE_SECRET    = os.getenv("EDGE_SYNC_SECRET", "some_random_secret_123")

S3_BUCKET      = "omnisight-bucket-storage"
S3_REGION      = "eu-north-1"
AWS_KEY        = os.getenv("AWS_ACCESS_KEY_ID",     "AKIA5E7OD3SPYQFWJ2EF")
AWS_SECRET     = os.getenv("AWS_SECRET_ACCESS_KEY", "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")

CAMERA_ID  = "cam-001"
TRACK_ID   = f"cam-001_vlmtest_{int(time.time() * 1000)}"


# ── Helpers ──────────────────────────────────────────────────────────────────
def ok(name): print(f"  [PASS] {name}")
def fail(name, reason): print(f"  [FAIL] {name}: {reason}")

def http(method, url, body=None, headers=None, timeout=90):
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", errors="replace"))
    except urllib.error.URLError as e:
        return 0, {"error": str(e.reason)}

def make_frame_b64(label: str, w=128, h=128) -> str:
    """Create a minimal valid JPEG (1×1 grey pixel) as base64 — tiny but real."""
    # Build a minimal PNG then convert via PIL, or just use a hardcoded JPEG.
    # This 1x1 grey JPEG is valid for any decoder including Qwen's vision encoder.
    GREY_JPEG = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
        b"IJB=>I\x1f\x1b\x1b!!$$$&&&\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04"
        b"\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa"
        b"\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n"
        b"\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz"
        b"\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99"
        b"\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7"
        b"\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5"
        b"\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1"
        b"\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00"
        b"\x00?\x00\xfb\xd6P\x00\x00\x00\x1f\xff\xd9"
    )
    return base64.b64encode(GREY_JPEG).decode("ascii")

def get_jwt():
    status, body = http("POST", f"{GATEWAY_URL}/api/v1/auth/login",
                        {"identifier": "admin@omnisight.com", "password": "Admin123!"})
    if status == 200:
        return body.get("data", {}).get("accessToken", "")
    return ""


# ── Tests ────────────────────────────────────────────────────────────────────
def test_vlm_health():
    print("\n[1] VLM EC2 Health")
    status, body = http("GET", f"{VLM_URL}/health", timeout=15)
    if status == 200:
        ok(f"health: {body}")
    else:
        fail("health", f"HTTP {status}: {body}")
    return status == 200


def test_vlm_analyze():
    print("\n[2] VLM /analyze  (real Qwen inference — may take 30-90s)")
    frames = [make_frame_b64(f"frame{i}") for i in range(4)]
    payload = {
        "event_id": f"test-{int(time.time())}",
        "camera_id": CAMERA_ID,
        "zone": "Main Zone",
        "anomaly_score_fusion": 0.78,
        "frames": frames,
    }
    t0 = time.time()
    status, body = http("POST", f"{VLM_URL}/analyze", payload, timeout=120)
    elapsed = time.time() - t0

    if status == 200:
        ok(f"analyze in {elapsed:.1f}s → crime_type={body.get('crime_type')} "
           f"score={body.get('anomaly_score_vlm')} people={body.get('people_count')}")
        print(f"     caption : {body.get('caption', '')[:100]}")
        print(f"     events  : {body.get('observed_events', [])[:2]}")
        print(f"     evidence: {body.get('anomaly_evidence', [])[:2]}")
        return body
    else:
        fail("analyze", f"HTTP {status}: {str(body)[:200]}")
        return None


def test_s3():
    print("\n[3] S3 clip upload")
    try:
        import boto3
        s3 = boto3.client("s3", region_name=S3_REGION,
                          aws_access_key_id=AWS_KEY,
                          aws_secret_access_key=AWS_SECRET)
        key = f"clips/{CAMERA_ID}/test_{int(time.time())}.txt"
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=b"omnisight-test", ContentType="text/plain")
        url = s3.generate_presigned_url("get_object",
                                        Params={"Bucket": S3_BUCKET, "Key": key},
                                        ExpiresIn=3600)
        ok(f"upload OK → {url[:80]}...")
        return url
    except Exception as e:
        fail("s3", str(e))
        return None


def test_analytics_vlm_ingest(vlm_result):
    print("\n[4] analytics-service VLM ingest")
    payload = {
        "track_id": TRACK_ID,
        "camera_id": CAMERA_ID,
        "zone": "Main Zone",
        "crime_type": vlm_result.get("crime_type", "suspicious") if vlm_result else "suspicious",
        "vlm_score": vlm_result.get("anomaly_score_vlm", "MEDIUM") if vlm_result else "MEDIUM",
        "people_count": vlm_result.get("people_count", 1) if vlm_result else 1,
        "caption": vlm_result.get("caption", "Test caption") if vlm_result else "Test caption",
        "events": vlm_result.get("observed_events", []) if vlm_result else [],
        "evidence": vlm_result.get("anomaly_evidence", []) if vlm_result else [],
        "video_url": "",
        "full_json": vlm_result or {},
    }
    status, body = http("POST", f"{ANALYTICS_URL}/api/v1/analytics/vlm/ingest", payload)
    if status == 201:
        ok(f"ingest → id={body.get('id')}")
        return body.get("id")
    else:
        fail("ingest", f"HTTP {status}: {body}")
        return None


def test_analytics_vlm_query():
    print("\n[5] analytics-service VLM query")
    status, body = http("GET", f"{ANALYTICS_URL}/api/v1/analytics/vlm/analyses?hours=1")
    if status == 200:
        ok(f"analyses: count={body.get('count')} in last 1h")
        for a in body.get("analyses", [])[:3]:
            print(f"     [{a['timestamp'][:19]}] {a['camera_id']} → {a['crime_type']} ({a['vlm_score']}) people={a['people_count']}")
            if a.get("caption"):
                print(f"       caption: {a['caption'][:100]}")
    else:
        fail("analyses", f"HTTP {status}: {body}")

    status, body = http("GET", f"{ANALYTICS_URL}/api/v1/analytics/vlm/summary")
    if status == 200:
        ok(f"summary: total={body.get('total')} by_type={body.get('by_crime_type')}")
    else:
        fail("summary", f"HTTP {status}: {body}")


def test_incident_classify(jwt):
    print("\n[6] incident-service edge/classify  (simulate VLM reclassifying)")
    # First create an incident via edge/sync
    sync_payload = {
        "edgeNodeCode": "edge-node-01",
        "detections": [{
            "cameraCode": CAMERA_ID,
            "trackId": TRACK_ID,
            "crimeType": "abnormal",
            "confidence": 0.82,
            "detectedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "modelVersion": "omnisight-ai-detection-v1.0",
            "aiMetadata": {"test": True},
        }],
    }
    status, body = http("POST", f"{INCIDENT_URL}/edge/sync", sync_payload,
                        {"x-edge-secret": EDGE_SECRET})
    if status not in (200, 201) or not body.get("success"):
        fail("edge/sync", f"HTTP {status}: {body}")
        return

    ok(f"edge/sync → incident created (success={body.get('success')} created={body.get('created')})")

    # Now reclassify it (simulating what VLM would do)
    time.sleep(0.5)
    classify_payload = {
        "trackId": TRACK_ID,
        "crimeType": "assault",
        "confidence": 0.91,
    }
    status, body = http("POST", f"{INCIDENT_URL}/edge/classify", classify_payload,
                        {"x-edge-secret": EDGE_SECRET})
    if status == 200 and body.get("success"):
        ok(f"edge/classify → crimeType updated to 'assault' (success={body.get('success')})")
    else:
        fail("edge/classify", f"HTTP {status}: {body}")


def test_full_analytics_check():
    print("\n[7] Full analytics dashboard sanity check")
    status, body = http("GET", f"{ANALYTICS_URL}/api/v1/analytics/surveillance/latest")
    if status == 200:
        cams = body.get("cameras", [])
        ok(f"surveillance/latest → {len(cams)} camera(s) reporting")
    else:
        fail("surveillance/latest", f"HTTP {status}")

    status, body = http("GET", f"{ANALYTICS_URL}/api/v1/analytics/vlm/analyses?hours=24")
    if status == 200:
        ok(f"vlm/analyses (24h) → {body.get('count')} total VLM analyses stored")
    else:
        fail("vlm/analyses", f"HTTP {status}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("   Omnisight VLM Pipeline — End-to-End Test")
    print("=" * 60)
    print(f"VLM EC2     : {VLM_URL}")
    print(f"Analytics   : {ANALYTICS_URL}")
    print(f"Incident    : {INCIDENT_URL}")
    print(f"S3 Bucket   : {S3_BUCKET}")
    print(f"Track ID    : {TRACK_ID}")

    print("\n--- Getting JWT ---")
    jwt = get_jwt()
    if jwt:
        print(f"  JWT: {jwt[:40]}...")
    else:
        print("  JWT: FAILED (some tests may skip)")

    vlm_ok  = test_vlm_health()
    vlm_res = test_vlm_analyze() if vlm_ok else None
    test_s3()
    test_analytics_vlm_ingest(vlm_res)
    test_analytics_vlm_query()
    test_incident_classify(jwt)
    test_full_analytics_check()

    print("\n" + "=" * 60)
    print("  Done. Check [PASS]/[FAIL] above for each step.")
    print("=" * 60)
