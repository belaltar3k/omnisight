# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the stack

Everything runs via Docker Compose from the `backend/` directory:

```bash
docker compose up -d --build   # first run or after code changes
docker compose up -d           # subsequent runs (no code change)
bash healthcheck.sh            # verify all 35 checks pass
```

To restart a single service after a source change (no full rebuild needed unless Dockerfile changes):

```bash
docker compose build <service-name>
docker compose up -d <service-name>
```

Service names: `auth-service`, `user-service`, `camera-service`, `incident-service`, `alert-service`, `api-gateway`, `analytics-service`.

## Local dev (without Docker for app services)

Infrastructure must still run via Docker:

```bash
docker compose up -d postgres user-postgres camera-postgres incident-postgres alert-postgres timescaledb redis zookeeper kafka rabbitmq
```

Then in separate terminals:

```bash
npm run start:dev -- auth-service       # :3001
npm run start:dev -- user-service       # :3004
npm run start:dev -- camera-service     # :3002
npm run start:dev -- incident-service   # :3003
npm run start:dev -- alert-service      # :3005
npm run start:dev -- api-gateway        # :3000

# Analytics (Python) — from apps/analytics-service/
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
python -m uvicorn app.main:app --port 3006 --reload
```

## Build & lint

```bash
npm run build                       # build all NestJS apps
npx nest build <service-name>       # build one service
npm run lint                        # ESLint across all apps and libs
npm run format                      # Prettier
npm test                            # Jest unit tests
npm run test:e2e                    # e2e (needs running infra)
```

## Architecture

### Overview

This is a **security camera incident-management platform**. Edge nodes (cameras/AI devices) detect suspicious activity and push detections to the backend. The backend creates incidents, routes push notifications, and feeds a time-series analytics dashboard.

All client traffic goes through the **API Gateway (:3000)**. The gateway is a pure HTTP proxy — it holds no business logic and no database. Every route in `api-gateway/src/modules/*-proxy/` is a thin `axios` call forwarded to the appropriate downstream service.

### Services and ports

| Service | Port | DB | Owns |
|---|---|---|---|
| api-gateway | 3000 | none | Routing, JWT validation at the edge |
| auth-service | 3001 | postgres:5432 `sentinel_auth` | Users, refresh tokens, password resets |
| camera-service | 3002 | postgres:5433 `sentinel_camera` | Zones, edge nodes, cameras |
| incident-service | 3003 | postgres:5434 `sentinel_incident` | Incidents, notes, timeline, Kafka producer |
| user-service | 3004 | postgres:5435 `sentinel_user` | User profiles, zone assignments |
| alert-service | 3005 | postgres:5436 `sentinel_alert` | FCM push notifications, device tokens, Kafka consumer |
| analytics-service | 3006 | timescaledb:5437 `omnisight_analytics` | Time-series metrics, dashboard, heatmap (Python/FastAPI) |

### NestJS monorepo layout

All NestJS services share one `package.json` and `node_modules` at the repo root. `nest-cli.json` declares each app as a separate project. The shared library at `libs/common/src/` exports:

- `ResponseInterceptor` + `ApiResponse` — every NestJS response is wrapped as `{success, statusCode, message, data}`. The analytics service does **not** use this wrapper (FastAPI returns its own shape).
- `AllExceptionsFilter` — unified error shape.
- `JwtAuthGuard` / `RolesGuard` / `@Roles()` — guards used identically across all services.
- `JwtStrategy` — each service that needs JWT registers this as a provider.
- `UserRole` enum — `admin`, `supervisor`, `security_guard`, plus internal service roles (`alert_service`, etc.).

### Authentication flow

1. Client registers/logs in through the gateway → gateway calls auth-service, then calls user-service to create a profile in one transaction with rollback on failure.
2. JWT `accessToken` (15 min) and `refreshToken` (7 days) are returned.
3. Protected routes on the gateway validate the JWT locally via `JwtAuthGuard`. The decoded payload (`{sub, email, role}`) is forwarded to downstream services as the `authorization` header — **downstream services trust the forwarded token, they do not re-validate signatures independently.**
4. The `GET /api/v1/auth/me` route on the gateway returns the decoded JWT payload directly without a downstream call.

### Internal service-to-service calls

Services communicate via HTTP (not a message bus for synchronous calls). Key patterns:

- **user-service** calls auth-service (`AUTH_SERVICE_URL`) to verify a user exists before creating a profile.
- **user-service** calls camera-service (`CAMERA_SERVICE_URL`) to validate zone IDs in zone-assignment logic.
- **alert-service** calls user-service (`USER_SERVICE_URL`) to fetch FCM device tokens by zone when dispatching push notifications.
- The gateway's `auth-proxy` calls both auth-service and user-service during registration (two-phase with rollback).

Internal calls from the gateway use `INTERNAL_SECRET` header (`x-internal-secret`). The user-service `profiles.controller.ts` checks this header on the `POST /profiles` route to prevent public access.

Alert-service generates its own long-lived JWT (10-year expiry, role `alert_service`) signed with `JWT_ACCESS_SECRET` for calls to user-service.

### Kafka event flow

`incident-service` → Kafka → `alert-service` + `analytics-service`

Topics:
- `sentinel.incident.new` — emitted when a new incident is confirmed (after edge classify upgrades from `detecting`)
- `sentinel.incident.status_changed` — emitted on every status transition

`alert-service` consumes both topics and sends Firebase Cloud Messaging push notifications to users assigned to the affected zone.

`analytics-service` (Python, `aiokafka`) consumes `sentinel.incident.new` and writes `IncidentMetric` rows to TimescaleDB hypertables.

Container-to-container Kafka address is `kafka:29092`. The `localhost:9092` listener is only for host-machine clients.

### Edge node flow (no JWT)

Edge nodes authenticate with a shared secret (`EDGE_SYNC_SECRET` env, `x-edge-secret` header):

1. `POST /api/v1/edge/sync` — batch detection payload `{edgeNodeCode, detections:[]}`. Creates incidents in `detecting` status. The incident-service looks up the camera by `cameraCode` → `edgeNodeCode` to resolve `cameraId`, `zoneId`, `edgeNodeId`.
2. `POST /api/v1/edge/classify` — flat `{trackId, crimeType, confidence}`. Upgrades a `detecting` incident to `new` and emits `sentinel.incident.new` to Kafka.

### Incident state machine

`detecting` → `new` → `acknowledged` → `investigating` → `dispatched` → `on_scene` → `resolved`

Side exits: any state → `false_positive`.

### Analytics service (Python)

Standalone FastAPI app at `apps/analytics-service/`. Not part of the NestJS monorepo — has its own `Dockerfile`, `requirements.txt`, and `docker-compose.yml` (superseded by the root compose). Database is initialized via `scripts/init_db.py` which runs `scripts/init_timescaledb.sql` to create hypertables. The entrypoint script runs this automatically in Docker.

The gateway proxies **all** `GET/POST/PATCH/DELETE /api/v1/analytics/**` requests to this service verbatim via `@All('*path')`.

### Environment variables

Secrets live in `backend/.env` (gitignored). Required variables:

```
JWT_ACCESS_SECRET
JWT_REFRESH_SECRET
INTERNAL_SECRET
EDGE_SYNC_SECRET
```

Optional (push notifications only, service starts without them):

```
FIREBASE_PROJECT_ID
FIREBASE_CLIENT_EMAIL
FIREBASE_PRIVATE_KEY
```

Each service in `docker-compose.yml` receives the env vars it needs — inter-service URLs (`AUTH_SERVICE_URL`, `CAMERA_SERVICE_URL`, `USER_SERVICE_URL`) must use Docker service names (e.g., `http://auth-service:3001`), never `localhost`.

### API testing

`sentinel-backend.postman_collection.json` contains the full collection. All routes go through the gateway on `:3000`. Run `healthcheck.sh` for a quick smoke test that doesn't require auth.
