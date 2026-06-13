-- Edge-specific tables for Sentinel AI Detection

-- Enable UUID extension just in case it's needed for generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE edge_detections (
    detection_id UUID PRIMARY KEY,
    camera_id UUID NOT NULL,
    crime_type VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    frame_data JSONB,
    keypoints JSONB,
    synced_to_cloud BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexing for fast queries and sync filtering
CREATE INDEX idx_edge_detections_synced ON edge_detections(synced_to_cloud) WHERE synced_to_cloud = FALSE;
CREATE INDEX idx_edge_detections_camera ON edge_detections(camera_id, detected_at);
CREATE INDEX idx_edge_detections_created_at ON edge_detections(created_at);

CREATE TABLE camera_status (
    camera_id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    last_frame_at TIMESTAMP,
    fps FLOAT,
    bitrate_kbps INT,
    error_count INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tracking active cameras
CREATE INDEX idx_camera_status_last_frame ON camera_status(last_frame_at);

CREATE TABLE sync_queue (
    queue_id UUID PRIMARY KEY,
    detection_id UUID NOT NULL REFERENCES edge_detections(detection_id) ON DELETE CASCADE,
    retry_count INT DEFAULT 0,
    last_retry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Priority picking for queue processing
CREATE INDEX idx_sync_queue_retry ON sync_queue(retry_count, last_retry_at);
