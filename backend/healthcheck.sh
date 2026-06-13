#!/usr/bin/env bash
# healthcheck.sh — ping every service in the Sentinel stack and report pass/fail
set -euo pipefail

PASS=0
FAIL=0
TIMEOUT=5

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}✗${NC} $1"; FAIL=$((FAIL + 1)); }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }

# ── helper: hit URL, any HTTP response = up, timeout/refused = down ──────────
http_check() {
  local label="$1" url="$2" expected_prefix="${3:-}"
  rm -f /tmp/hc_body
  code=$(curl -s -o /tmp/hc_body -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || true)
  if [[ -z "$code" || "$code" == "000" ]]; then
    fail "$label  →  no response (connection refused or timeout)"
    return
  fi
  if [[ -n "$expected_prefix" && ! "$code" == ${expected_prefix}* ]]; then
    local body
    body=$(cat /tmp/hc_body 2>/dev/null | head -c 120)
    fail "$label  →  HTTP $code  ($body)"
    return
  fi
  ok "$label  →  HTTP $code"
}

# ── helper: check docker container is running ─────────────────────────────────
container_check() {
  local label="$1" name="$2"
  local state
  state=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "missing")
  if [[ "$state" == "running" ]]; then
    ok "$label  →  running"
  else
    fail "$label  →  $state"
  fi
}

# ── helper: TCP port reachability ─────────────────────────────────────────────
tcp_check() {
  local label="$1" host="$2" port="$3"
  if timeout "$TIMEOUT" bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
    ok "$label  →  port $port open"
  else
    fail "$label  →  port $port unreachable"
  fi
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Sentinel Backend — Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─── 1. Container status ───────────────────────────────────────────────────────
echo ""
echo "[ Docker containers ]"
container_check "postgres (auth)"      sentinel-auth-postgres
container_check "postgres (user)"      sentinel-user-postgres
container_check "postgres (camera)"    sentinel-camera-postgres
container_check "postgres (incident)"  sentinel-incident-postgres
container_check "postgres (alert)"     sentinel-alert-postgres
container_check "timescaledb"          omnisight-timescaledb
container_check "redis"                sentinel-redis
container_check "zookeeper"            sentinel-zookeeper
container_check "kafka"                sentinel-kafka
container_check "rabbitmq"             sentinel-rabbitmq
container_check "auth-service"         sentinel-auth-service
container_check "user-service"         sentinel-user-service
container_check "camera-service"       sentinel-camera-service
container_check "incident-service"     sentinel-incident-service
container_check "alert-service"        sentinel-alert-service
container_check "analytics-service"    omnisight-analytics-service
container_check "api-gateway"          sentinel-api-gateway
container_check "edge-database"        sentinel-edge-database
container_check "edge-cache"           sentinel-edge-cache
container_check "video-ingestion"      sentinel-video-ingestion
container_check "monitoring-agent"     sentinel-monitoring-agent
container_check "node-exporter"        sentinel-node-exporter

# ─── 2. HTTP reachability ─────────────────────────────────────────────────────
echo ""
echo "[ HTTP endpoints ]"

# Services with /health routes
http_check "api-gateway       :3000/health"      "http://localhost:3000/health"          "2"
http_check "camera-service    :3002/health"      "http://localhost:3002/health"          "2"
http_check "user-service      :3004/health"      "http://localhost:3004/health"          "2"
http_check "analytics-service :3006/health"      "http://localhost:3006/health"          "2"

# Services without /health — any HTTP response (incl. 401/404) means up
http_check "auth-service      :3001/auth/login"  "http://localhost:3001/auth/login"      ""
http_check "incident-service  :3003/incidents"   "http://localhost:3003/incidents"       ""
http_check "alert-service     :3005/device-tokens" "http://localhost:3005/device-tokens" ""

# Edge service metrics endpoints
http_check "video-ingestion   :8000/metrics"     "http://localhost:8000/metrics"         "2"
http_check "monitoring-agent  :9101/metrics"     "http://localhost:9101/metrics"         "2"
http_check "node-exporter     :9100/metrics"     "http://localhost:9100/metrics"         "2"

# ─── 3. Infrastructure TCP reachability ──────────────────────────────────────
echo ""
echo "[ Infrastructure TCP ]"

tcp_check "postgres (auth)"      localhost 5432
tcp_check "postgres (user)"      localhost 5435
tcp_check "postgres (camera)"    localhost 5433
tcp_check "postgres (incident)"  localhost 5434
tcp_check "postgres (alert)"     localhost 5436
tcp_check "timescaledb"          localhost 5437
tcp_check "edge-database"        localhost 5438
tcp_check "redis"                localhost 6379
tcp_check "edge-cache"           localhost 6380
tcp_check "kafka"                localhost 9092
tcp_check "zookeeper"            localhost 2181
tcp_check "rabbitmq amqp"        localhost 5672
tcp_check "rabbitmq management"  localhost 15672

# ─── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((PASS + FAIL))
if [[ $FAIL -eq 0 ]]; then
  echo -e "  ${GREEN}All $TOTAL checks passed${NC}"
else
  echo -e "  ${RED}$FAIL of $TOTAL checks failed${NC}  (${GREEN}$PASS passed${NC})"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

[[ $FAIL -eq 0 ]]
