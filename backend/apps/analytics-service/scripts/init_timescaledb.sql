-- scripts/init_timescaledb.sql

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1. Create Incident Metrics Table
CREATE TABLE IF NOT EXISTS incident_metrics (
    id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    incident_id UUID NOT NULL,
    crime_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    zone_id UUID NOT NULL,
    camera_id UUID NOT NULL,
    confidence FLOAT NOT NULL,
    status VARCHAR(50) NOT NULL,
    is_false_positive BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id, timestamp)
);

-- Convert to Hypertable (Partitions data by timestamp into 1-day chunks)
SELECT create_hypertable('incident_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

-- 2. Create Camera Metrics Table
CREATE TABLE IF NOT EXISTS camera_metrics (
    id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    camera_id UUID NOT NULL,
    camera_code VARCHAR(100) NOT NULL,
    uptime_percent FLOAT NOT NULL,
    avg_fps FLOAT NOT NULL,
    total_detections INTEGER DEFAULT 0,
    incidents_generated INTEGER DEFAULT 0,
    false_positive_rate FLOAT DEFAULT 0.0,
    avg_detection_latency_ms FLOAT DEFAULT 0.0,
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable('camera_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

-- 3. Create Response Time Metrics Table
CREATE TABLE IF NOT EXISTS response_time_metrics (
    id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    incident_id UUID NOT NULL,
    crime_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    time_to_acknowledge_seconds INTEGER,
    time_to_resolve_seconds INTEGER,
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable('response_time_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

-- 4. Create Surveillance Metrics Table (from surveillance_analytics module)
CREATE TABLE IF NOT EXISTS surveillance_metrics (
    id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    camera_id VARCHAR(100) NOT NULL,
    persons INTEGER DEFAULT 0,
    vehicles INTEGER DEFAULT 0,
    total_alerts INTEGER DEFAULT 0,
    modules JSONB DEFAULT '{}',
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable('surveillance_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

-- 5. Create VLM Analysis Table (stores Qwen2.5-VL-7B analysis results per anomaly event)
CREATE TABLE IF NOT EXISTS vlm_analyses (
    id UUID DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    track_id VARCHAR(255) NOT NULL,
    camera_id VARCHAR(100) NOT NULL,
    zone VARCHAR(255),
    crime_type VARCHAR(50) NOT NULL DEFAULT 'abnormal',
    vlm_score VARCHAR(20),
    people_count INTEGER DEFAULT 0,
    caption TEXT,
    events JSONB DEFAULT '[]',
    evidence JSONB DEFAULT '[]',
    video_url TEXT,
    full_json JSONB DEFAULT '{}',
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable('vlm_analyses', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

-- Create some helpful indexes for faster querying
CREATE INDEX IF NOT EXISTS ix_incident_metrics_crime_type ON incident_metrics (crime_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_incident_metrics_zone_id ON incident_metrics (zone_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_surveillance_metrics_camera_id ON surveillance_metrics (camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_vlm_analyses_camera_id ON vlm_analyses (camera_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_vlm_analyses_crime_type ON vlm_analyses (crime_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_vlm_analyses_track_id ON vlm_analyses (track_id);