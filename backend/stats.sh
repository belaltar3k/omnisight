#!/usr/bin/env bash
# OmniSight stats dashboard

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

header() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${RESET}"; }
kv()     { printf "  %-28s ${GREEN}%s${RESET}\n" "$1" "$2"; }
warn()   { printf "  %-28s ${YELLOW}%s${RESET}\n" "$1" "$2"; }
alert()  { printf "  %-28s ${RED}%s${RESET}\n" "$1" "$2"; }

# ── AI Detection ─────────────────────────────────────────────────────────────
header "AI Detection  (port 8010)"

READINESS=$(curl -sf http://localhost:8010/readiness 2>/dev/null)
CAMERAS=$(curl -sf http://localhost:8010/api/v1/cameras 2>/dev/null)

if [ -z "$READINESS" ]; then
  alert "Status" "UNREACHABLE"
else
  STATUS=$(echo "$READINESS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])" 2>/dev/null)
  DETECTORS=$(echo "$READINESS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(d['detectors']))" 2>/dev/null)
  kv "Status" "$STATUS"
  kv "Loaded detectors" "$DETECTORS"

  echo "$READINESS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for name, t in d.get('load_times', {}).items():
    print(f'  {name:<28} loaded in {t:.1f}s')
" 2>/dev/null
fi

if [ -n "$CAMERAS" ]; then
  echo "$CAMERAS" | python3 -c "
import sys, json
cameras = json.load(sys.stdin)
for cam in cameras:
    anomaly = cam['anomaly_active']
    score   = cam['last_fusion_score']
    status  = cam['status']
    fps     = cam['fps']
    sent    = cam['total_detections_sent']
    print(f\"  {'Camera':<28} {cam['camera_id']}\")
    print(f\"  {'Status':<28} {status}  ({fps:.1f} fps)\")
    print(f\"  {'Fusion score':<28} {score:.4f}\")
    print(f\"  {'Anomaly active':<28} {'YES' if anomaly else 'no'}\")
    print(f\"  {'Detections dispatched':<28} {sent}\")
    print(f\"  {'Active detectors':<28} {', '.join(cam['active_detectors'])}\")
" 2>/dev/null
fi

# ── Incidents (DB) ────────────────────────────────────────────────────────────
header "Incidents  (postgres)"

INCIDENT_STATS=$(docker exec sentinel-incident-postgres psql -U sentinel -d sentinel_incident -t -A -F'|' -c "
SELECT
  COUNT(*)                                          AS total,
  COUNT(*) FILTER (WHERE status = 'new')            AS new,
  COUNT(*) FILTER (WHERE status = 'detecting')      AS detecting,
  COUNT(*) FILTER (WHERE status = 'resolved')       AS resolved,
  COUNT(*) FILTER (WHERE status = 'false_positive') AS false_positive,
  COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') AS last_hour,
  ROUND(AVG(confidence)::numeric, 3)                AS avg_confidence,
  MAX(confidence)                                   AS max_confidence
FROM incidents
WHERE deleted_at IS NULL;" 2>/dev/null)

if [ -n "$INCIDENT_STATS" ]; then
  IFS='|' read -r total new detecting resolved fp last_hour avg_conf max_conf <<< "$INCIDENT_STATS"
  kv "Total incidents" "$total"
  kv "New" "$new"
  kv "Detecting" "$detecting"
  kv "Resolved" "$resolved"
  kv "False positives" "$fp"
  kv "Last hour" "$last_hour"
  kv "Avg confidence" "$avg_conf"
  kv "Max confidence" "$max_conf"
fi

echo ""
echo "  Recent incidents:"
docker exec sentinel-incident-postgres psql -U sentinel -d sentinel_incident -t -A -F'|' -c "
SELECT camera_code, crime_type, confidence, status, priority, detected_at
FROM incidents
WHERE deleted_at IS NULL
ORDER BY detected_at DESC
LIMIT 5;" 2>/dev/null | while IFS='|' read -r cam crime conf stat pri at; do
  printf "  ${BOLD}%-10s${RESET} %-12s conf=%-6s %-8s %-8s  %s\n" \
    "$cam" "$crime" "$conf" "$stat" "$pri" "$at"
done

# ── Edge Node Metrics (port 9101) ─────────────────────────────────────────────
header "Edge Node Metrics  (port 9101)"

METRICS=$(curl -sf http://localhost:9101/metrics 2>/dev/null)

if [ -z "$METRICS" ]; then
  alert "Status" "UNREACHABLE"
else
  parse_metric() { echo "$METRICS" | grep "^$1{" | awk '{print $NF}'; }

  CPU=$(parse_metric "node_cpu_usage_percent")
  MEM=$(parse_metric "node_memory_usage_percent")
  DISK=$(parse_metric "node_disk_usage_percent")
  RX=$(parse_metric "node_network_receive_bytes")
  TX=$(parse_metric "node_network_transmit_bytes")
  GPU_UTIL=$(parse_metric "gpu_utilization_percent")
  GPU_TEMP=$(parse_metric "gpu_temperature_celsius")
  GPU_MEM=$(parse_metric "gpu_memory_used_bytes")
  LATENCY=$(parse_metric "detection_latency_seconds")

  kv "CPU usage" "${CPU}%"
  [ "$(echo "$MEM > 80" | bc -l 2>/dev/null)" = "1" ] \
    && warn "Memory usage" "${MEM}%" \
    || kv "Memory usage" "${MEM}%"
  [ "$(echo "${DISK:-0} > 90" | bc -l 2>/dev/null)" = "1" ] \
    && alert "Disk usage" "${DISK}%" \
    || kv "Disk usage" "${DISK}%"
  kv "Network RX" "$(echo "$RX" | awk '{printf "%.1f KB", $1/1024}')"
  kv "Network TX" "$(echo "$TX" | awk '{printf "%.1f KB", $1/1024}')"

  if [ -n "$GPU_UTIL" ]; then
    kv "GPU utilization" "${GPU_UTIL}%"
    kv "GPU temperature" "${GPU_TEMP}°C"
    kv "GPU memory used" "$(echo "$GPU_MEM" | awk '{printf "%.0f MB", $1/1024/1024}')"
  else
    warn "GPU metrics" "not reported (check monitoring-agent)"
  fi

  [ -n "$LATENCY" ] && kv "Detection latency" "${LATENCY}s"
fi

# ── Container Health ──────────────────────────────────────────────────────────
header "Container Health"

docker ps --format '{{.Names}}|{{.Status}}' 2>/dev/null \
  | grep sentinel\|omnisight \
  | while IFS='|' read -r name status; do
    if echo "$status" | grep -q "unhealthy\|Exited\|Restarting"; then
      alert "$name" "$status"
    elif echo "$status" | grep -q "healthy"; then
      kv "$name" "$status"
    else
      printf "  %-28s %s\n" "$name" "$status"
    fi
  done

echo ""
