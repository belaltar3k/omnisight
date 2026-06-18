import time
import json
import logging
import os
import psycopg2
import redis
from datetime import datetime
from prometheus_client import start_http_server, Gauge
from src.core.config import config
from src.services.camera_worker import CameraWorker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VideoIngestion")

# Expose metrics to Monitoring Agent
CAMERA_STATUS = Gauge('camera_online', 'Camera connection status', ['camera_id'])
CAMERA_FPS = Gauge('camera_fps', 'Current frames per second', ['camera_id'])
CAMERA_DROPS = Gauge('camera_frame_drops', 'Dropped frames count', ['camera_id'])
CAMERA_BITRATE = Gauge('camera_bitrate_kbps', 'Current Bitrate in Kbps', ['camera_id'])

# Redis client
REDIS_HOST = os.environ.get("REDIS_HOST", "edge-cache")
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

def get_pg_connection():
    try:
        return psycopg2.connect(
            host=os.environ.get("PG_HOST", "edge-database"),
            port=5432,
            database=os.environ.get("POSTGRES_DB", "postgres"),
            user=os.environ.get("POSTGRES_USER", "postgres"),
            password=os.environ.get("POSTGRES_PASSWORD", "postgres")
        )
    except Exception:
        return None

def update_external_stores(cam):
    # 1. Update Redis (TTL: 30s)
    if redis_client:
        try:
            status_data = {
                "status": cam.status,
                "last_frame_at": datetime.utcnow().isoformat(),
                "fps": cam.current_fps,
                "bitrate_kbps": cam.current_bitrate_kbps
            }
            redis_client.setex(f"camera:status:{cam.camera_id}", 30, json.dumps(status_data))
        except Exception:
            pass
            
    # 2. Update PostgreSQL Edge Database
    conn = get_pg_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # We need a proper UUID per camera for the database schema, 
                # but cam.camera_id is string "cam-001". Using a deterministic or existing UUID logic is required.
                # For simplicity in edge nodes, let's assume we map string id to a static UUID 
                # or the db accepts string. The schema requires UUID.
                # Let's generate a deterministic UUID based on string to satisfy 'UUID PRIMARY KEY'.
                import uuid
                cam_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, cam.camera_id))
                
                cur.execute("""
                    INSERT INTO camera_status (camera_id, status, last_frame_at, fps, bitrate_kbps, error_count, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (camera_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_frame_at = EXCLUDED.last_frame_at,
                        fps = EXCLUDED.fps,
                        bitrate_kbps = EXCLUDED.bitrate_kbps,
                        updated_at = NOW();
                """, (cam_uuid, cam.status, datetime.utcnow(), cam.current_fps, cam.current_bitrate_kbps, 0))
                conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

def main():
    logger.info("Starting Video Ingestion Service [ENTERPRISE MODE]...")
    
    start_http_server(8000)
    
    cameras = []
    for i, url in enumerate(config.RTSP_URLS):
        cam_id = f"cam-{i+1:03d}"
        worker = CameraWorker(cam_id, url)
        worker.start()
        cameras.append(worker)

    try:
        while True:
            # Publish metrics
            for cam in cameras:
                CAMERA_STATUS.labels(camera_id=cam.camera_id).set(1 if cam.status == "online" else 0)
                CAMERA_FPS.labels(camera_id=cam.camera_id).set(cam.current_fps)
                CAMERA_DROPS.labels(camera_id=cam.camera_id).set(cam.drop_count)
                CAMERA_BITRATE.labels(camera_id=cam.camera_id).set(cam.current_bitrate_kbps)
                
                # Push to Redis/PG
                update_external_stores(cam)
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        for cam in cameras:
            cam.stop()

if __name__ == "__main__":
    main()
