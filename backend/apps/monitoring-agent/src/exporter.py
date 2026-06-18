import os
import time
import psutil
import logging
from prometheus_client import start_http_server, Gauge, Counter
import pynvml
import redis

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Node Config
NODE_ID = os.environ.get("EDGE_NODE_ID", "edge-cairo-01")
REDIS_HOST = os.environ.get("REDIS_HOST", "edge-cache")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# --- Define Prometheus Metrics ---

# System Metrics
LABELS_SYS = ["node_id"]
LABELS_DISK = ["node_id", "mount"]
LABELS_NET = ["node_id", "interface"]

NODE_CPU = Gauge("node_cpu_usage_percent", "System CPU usage percent", LABELS_SYS)
NODE_MEM = Gauge("node_memory_usage_percent", "System memory usage percent", LABELS_SYS)
NODE_DISK = Gauge("node_disk_usage_percent", "System disk usage percent", LABELS_DISK)
NODE_NET_RX = Gauge("node_network_receive_bytes", "Network receive bytes", LABELS_NET)
NODE_NET_TX = Gauge("node_network_transmit_bytes", "Network transmit bytes", LABELS_NET)

# GPU Metrics
LABELS_GPU = ["node_id", "gpu"]
GPU_UTIL = Gauge("gpu_utilization_percent", "GPU utilization percent", LABELS_GPU)
GPU_TEMP = Gauge("gpu_temperature_celsius", "GPU temperature in Celsius", LABELS_GPU)
GPU_MEM = Gauge("gpu_memory_used_bytes", "GPU memory used in bytes", LABELS_GPU)

# Application Metrics
LABELS_CAM = ["node_id", "camera_id"]
LABELS_CRIME = ["node_id", "crime_type"]

APP_LATENCY = Gauge("detection_latency_seconds", "Detection latency in seconds", LABELS_CAM)
APP_FPS = Gauge("detection_fps", "Detection FPS", LABELS_CAM)
APP_DETECTIONS = Counter("detection_total", "Total detections by crime type", LABELS_CRIME)
APP_CAM_ONLINE = Gauge("camera_online", "Camera online status (1=online, 0=offline)", LABELS_CAM)

# Optional Redis connection for pulling dynamic app metrics from Service 4 (Edge Cache)
def get_redis_client():
    try:
        return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None

def init_gpu():
    try:
        pynvml.nvmlInit()
        return pynvml.nvmlDeviceGetCount()
    except Exception as e:
        logger.warning(f"NVML could not be initialized (No NVIDIA GPU found or driver missing): {e}")
        return 0

def collect_system_metrics():
    # CPU
    NODE_CPU.labels(node_id=NODE_ID).set(psutil.cpu_percent(interval=None))
    
    # Memory
    mem = psutil.virtual_memory()
    NODE_MEM.labels(node_id=NODE_ID).set(mem.percent)
    
    # Disk (using the root partition or container mounted equivalent)
    try:
        disk = psutil.disk_usage('/')
        NODE_DISK.labels(node_id=NODE_ID, mount="/").set(disk.percent)
    except Exception:
        pass
        
    # Network
    net_io = psutil.net_io_counters(pernic=True)
    # Using eth0 as default priority interface based on spec, or grab the first viable interface
    for interface, stats in net_io.items():
        if interface == "lo": continue
        NODE_NET_RX.labels(node_id=NODE_ID, interface=interface).set(stats.bytes_recv)
        NODE_NET_TX.labels(node_id=NODE_ID, interface=interface).set(stats.bytes_sent)

def collect_gpu_metrics(gpu_count):
    if gpu_count == 0:
        return
        
    try:
        for i in range(gpu_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            str_i = str(i)
            GPU_UTIL.labels(node_id=NODE_ID, gpu=str_i).set(util.gpu)
            GPU_TEMP.labels(node_id=NODE_ID, gpu=str_i).set(temp)
            GPU_MEM.labels(node_id=NODE_ID, gpu=str_i).set(mem.used)
    except Exception as e:
        logger.error(f"Error collecting GPU metrics: {e}")

import json

def collect_app_metrics(r_client):
    if not r_client:
        return

    try:
        # Discover all active cameras by scanning Redis keys written by video-ingestion
        keys = r_client.keys("camera:status:*")
    except Exception as e:
        logger.warning(f"Redis scan failed: {e}")
        return

    for key in keys:
        camera_id = key.split("camera:status:", 1)[-1]
        try:
            raw = r_client.get(key)
            if not raw:
                continue
            data = json.loads(raw)
            is_online = 1 if data.get("status") == "online" else 0
            fps = float(data.get("fps", 0))

            APP_CAM_ONLINE.labels(node_id=NODE_ID, camera_id=camera_id).set(is_online)
            APP_FPS.labels(node_id=NODE_ID, camera_id=camera_id).set(fps)
            # latency is not published by video-ingestion; zero it out rather than stub
            APP_LATENCY.labels(node_id=NODE_ID, camera_id=camera_id).set(0)
        except Exception as e:
            logger.warning(f"Failed to parse status for {key}: {e}")

def main():
    exporter_port = int(os.environ.get("EXPORTER_PORT", 9101))
    start_http_server(exporter_port)
    logger.info(f"Monitoring Agent custom exporter started on port {exporter_port}")
    
    gpu_count = init_gpu()
    r_client = get_redis_client()
    
    try:
        while True:
            collect_system_metrics()
            collect_gpu_metrics(gpu_count)
            collect_app_metrics(r_client)
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Agent stopped.")
    finally:
        if gpu_count > 0:
            pynvml.nvmlShutdown()

if __name__ == '__main__':
    main()
