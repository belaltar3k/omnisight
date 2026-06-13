-- Set up pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Data Retention: Detections (7 days)
-- Runs daily at 01:00 AM
SELECT cron.schedule('cleanup_edge_detections', '0 1 * * *', $$
    DELETE FROM edge_detections 
    WHERE created_at < NOW() - INTERVAL '7 days';
$$);

-- Data Retention: Camera status (30 days)
-- Runs daily at 01:15 AM
SELECT cron.schedule('cleanup_camera_status', '15 1 * * *', $$
    DELETE FROM camera_status 
    WHERE updated_at < NOW() - INTERVAL '30 days';
$$);

-- Data Retention: Sync queue (Until successful or 10 retries)
-- Runs daily at 01:30 AM
SELECT cron.schedule('cleanup_sync_queue', '30 1 * * *', $$
    DELETE FROM sync_queue 
    WHERE retry_count >= 10;
$$);
