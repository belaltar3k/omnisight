import sys
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

# Add the root directory to the python path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.incident_metric import IncidentMetric
from app.models.camera_metric import CameraMetric
from app.models.response_time import ResponseTimeMetric

# --- Constants & Enums ---
CRIME_TYPES = ['theft', 'shoplifting', 'assault', 'vandalism', 'fire', 'weapon', 'intrusion', 'accident', 'suspicious', 'abnormal']
STATUSES = ['new', 'acknowledged', 'investigating', 'dispatched', 'on_scene', 'resolved', 'false_positive']

# Generate consistent UUIDs for our fake environment
ZONES = {f"Zone {i}": uuid.uuid4() for i in range(1, 6)}
CAMERAS = []
for i in range(1, 21):
    zone_name, zone_id = random.choice(list(ZONES.items()))
    CAMERAS.append({
        "id": uuid.uuid4(),
        "code": f"CAM-{zone_name.replace(' ', '').upper()}-{i:02d}",
        "zone_id": zone_id
    })

def calculate_priority(crime_type: str, confidence: float) -> str:
    if crime_type in ['assault', 'fire', 'weapon']:
        return 'critical'
    if confidence > 0.90 or crime_type in ['theft', 'vandalism']:
        return 'high'
    if confidence > 0.70:
        return 'medium'
    return 'low'

def generate_data(days_back: int = 30, num_incidents: int = 1500):
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    
    print(f"Generating data for the past {days_back} days...")
    
    incidents_to_insert = []
    response_times_to_insert = []
    
    # 1. Generate Incidents and Response Times
    for _ in range(num_incidents):
        # Random time in the past X days
        random_seconds = random.randint(0, days_back * 24 * 60 * 60)
        detected_at = now - timedelta(seconds=random_seconds)
        
        camera = random.choice(CAMERAS)
        crime_type = random.choice(CRIME_TYPES)
        confidence = round(random.uniform(0.60, 0.99), 3)
        priority = calculate_priority(crime_type, confidence)
        status = random.choices(STATUSES, weights=[5, 10, 10, 5, 5, 60, 5])[0]
        is_false_pos = (status == 'false_positive')
        
        incident_id = uuid.uuid4()
        
        incident = IncidentMetric(
            timestamp=detected_at,
            incident_id=incident_id,
            crime_type=crime_type,
            priority=priority,
            zone_id=camera["zone_id"],
            camera_id=camera["id"],
            confidence=confidence,
            status=status,
            is_false_positive=is_false_pos
        )
        incidents_to_insert.append(incident)
        
        # If the incident progressed past 'new', it has response times
        if status not in ['new', 'false_positive']:
            # Critical incidents get faster responses
            base_ack = 30 if priority == 'critical' else 120
            base_res = 600 if priority == 'critical' else 1800
            
            ack_time = random.randint(base_ack // 2, base_ack * 3)
            # Only full resolution gets a resolve time
            res_time = random.randint(base_res // 2, base_res * 3) if status == 'resolved' else None
            
            response_times_to_insert.append(ResponseTimeMetric(
                timestamp=detected_at,
                incident_id=incident_id,
                crime_type=crime_type,
                priority=priority,
                time_to_acknowledge_seconds=ack_time,
                time_to_resolve_seconds=res_time
            ))

    # 2. Generate Camera Metrics (1 entry per camera per day)
    camera_metrics_to_insert = []
    for day in range(days_back):
        metric_date = now - timedelta(days=day)
        for cam in CAMERAS:
            uptime = round(random.uniform(95.0, 100.0), 2)
            fps = round(random.uniform(24.0, 30.0), 1)
            
            camera_metrics_to_insert.append(CameraMetric(
                timestamp=metric_date,
                camera_id=cam["id"],
                camera_code=cam["code"],
                uptime_percent=uptime,
                avg_fps=fps,
                total_detections=random.randint(100, 5000),
                incidents_generated=random.randint(0, 10),
                false_positive_rate=round(random.uniform(0.01, 0.15), 3),
                avg_detection_latency_ms=round(random.uniform(1500, 2500), 1)
            ))

    try:
        print(f"Inserting {len(incidents_to_insert)} incidents...")
        db.bulk_save_objects(incidents_to_insert)
        
        print(f"Inserting {len(response_times_to_insert)} response times...")
        db.bulk_save_objects(response_times_to_insert)
        
        print(f"Inserting {len(camera_metrics_to_insert)} camera daily metrics...")
        db.bulk_save_objects(camera_metrics_to_insert)
        
        db.commit()
        print("✅ Dummy data successfully seeded into TimescaleDB!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_data(days_back=30, num_incidents=1500)