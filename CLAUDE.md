# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Repository Layout

```
omnisight/
├── backend/                  NestJS monorepo (all TypeScript microservices share one package.json)
│   ├── apps/
│   │   ├── api-gateway/      Port 3000 — JWT-enforced reverse proxy for all other services
│   │   ├── auth-service/     Port 3001 — registration, login, JWT issue/refresh
│   │   ├── user-service/     Port 3004 — profiles + zone assignments
│   │   ├── camera-service/   Port 3012 — zones, edge nodes, cameras
│   │   ├── incident-service/ Port 3003 — full incident lifecycle + timeline/notes
│   │   ├── alert-service/    Port 3005 — Kafka-triggered alerts + FCM push
│   │   ├── analytics-service/Port 3006 — Python FastAPI: stats, chatbot, VLM, surveillance
│   │   ├── ai-detection/     Port 8010 — Python FastAPI: runs ML models, streams MJPEG
│   │   ├── video-ingestion/  Python: reads RTSP → POSIX shared memory (IPC)
│   │   ├── snapshot-service/ Python: periodic JPEG snapshots from shared memory
│   │   ├── monitoring-agent/ Python: Prometheus metrics exporter for edge health
│   │   ├── edge-database/    Postgres 16 for edge-local storage (port 5438)
│   │   └── edge-cache/       Redis 7 for edge-local cache (port 6380)
│   ├── libs/common/          Shared NestJS guards, interceptors, decorators, enums
│   └── docker-compose.yml    Full stack (infra + all services)
├── ai/                       Standalone AI pipeline (research + training)
│   ├── pipeline/             WeightedFusionEngine, PipelineRunner, config
│   ├── components/           crime_skelnet, video_mae, weapon_detection, paan, tracking
│   └── surveillance_analytics/ 19-module SA layer (crowd, traffic, loitering, etc.)
├── frontend/                 Angular 17 standalone (Tailwind + custom design system)
├── vlm_api/                  Qwen-VL wrapper — separate deploy, called by ai-detection
└── FRONTEND_INTEGRATION.md  Full API contract + integration spec for frontend dev
```

---

## Commands

### Backend (NestJS monorepo — run from `backend/`)

```bash
# Start all infrastructure (Postgres ×5, TimescaleDB, Redis, Kafka, RabbitMQ)
docker compose up -d postgres user-postgres camera-postgres incident-postgres alert-postgres timescaledb redis kafka zookeeper

# Run a single service in dev/watch mode
nest start auth-service --watch
nest start api-gateway --watch

# Run all tests
npm test

# Run tests for one app
npx jest --testPathPattern=apps/auth-service

# Lint
npm run lint

# Build all apps for production
npm run build
```

### Analytics Service (Python FastAPI — run from `backend/apps/analytics-service/`)

```bash
pip install -r requirements.txt

# Initialize TimescaleDB schema
python scripts/init_db.py

# Start dev server
uvicorn app.main:app --host 0.0.0.0 --port 3006 --reload

# Run tests
pytest
```

Copy `.env.example` to `.env` and set `DATABASE_URL`, `REDIS_URL`, `KAFKA_BOOTSTRAP_SERVERS` before running locally.

### AI Detection Service (Docker only — build from repo root)

```bash
# Build (context must be repo root — Dockerfile copies from ai/ and backend/apps/ai-detection/)
docker build -f backend/apps/ai-detection/Dockerfile -t omnisight-ai-detection .

# Run with GPU + host RTSP access
docker run --rm --gpus all \
  --add-host host.docker.internal:host-gateway \
  -v $(pwd)/ai/weights:/app/weights:ro \
  -e RTSP_URLS='["rtsp://host.docker.internal:8554/camera1"]' \
  -e DISABLED_MODELS='["video_mae"]' \
  -e INCIDENT_SERVICE_URL=http://host.docker.internal:3003 \
  -e ANALYTICS_SERVICE_URL=http://host.docker.internal:3006 \
  -e EDGE_SYNC_SECRET=some_random_secret_123 \
  -p 8010:8010 \
  omnisight-ai-detection
```

### Standalone AI Pipeline (run from `ai/`)

```bash
python run_pipeline.py --video path/to/video.mp4 --device cuda
python run_pipeline.py --video clip.mp4 --disable paan video_mae --threshold 0.55 --json result.json

# Individual components
python -m components.paan.inference.run_paan --audio input.wav
python -m components.crime_skelnet.inference.video_inference --video input.mp4
```

### Frontend (run from `frontend/`)

```bash
npm install
npm run dev          # ng serve --host 0.0.0.0
npm run build        # production build
npm run typecheck    # tsc --noEmit, no test runner
```

### Full Stack

```bash
cd backend && docker compose up -d     # all services + infrastructure
```

The root `backend/.env` controls secrets and toggles for the whole stack. Key variables:

| Variable | Purpose |
|----------|---------|
| `JWT_ACCESS_SECRET` / `JWT_REFRESH_SECRET` | Shared across all NestJS services |
| `EDGE_SYNC_SECRET` | Header secret used by ai-detection when posting to incident-service |
| `RTSP_URLS` | JSON array of RTSP stream URLs for video-ingestion and ai-detection |
| `AI_DISABLED_MODELS` | JSON array — e.g. `["video_mae"]` to skip VideoMAE |
| `EDGE_NODE_ID` | Must match the edge node `code` registered in camera-service DB |

---

## Architecture — Key Concepts

### API Response Envelope

Every NestJS response goes through `ResponseInterceptor` (`libs/common/src/responses/response.interceptor.ts`), wrapping all data in:

```json
{ "success": true, "data": { ... }, "message": "Success" }
```

Frontend must unwrap `response.data.*` — not read top-level fields directly.

### Auth Login

The login body field is `identifier` (not `email`). The auth service accepts either email or username in that field. This is a common gotcha — the field name is `identifier` everywhere: in the API, in the Postman collection, and in the Angular `ILoginRequest` interface.

### API Gateway Routing

The gateway (`apps/api-gateway`) is a thin pass-through: it validates the JWT, then forwards `req.originalUrl` verbatim to the target service. There is no path rewriting. Every downstream service runs its own JWT validation independently as well.

Routes proxied:
- `/api/v1/auth/*` → auth-service:3001
- `/api/v1/profiles/*`, `/api/v1/zone-assignments/*` → user-service:3004
- `/api/v1/zones/*`, `/api/v1/edge-nodes/*`, `/api/v1/cameras/*`, `/api/v1/device-tokens/*` → camera-service:3012
- `/api/v1/incidents/*`, `/api/v1/edge/*` → incident-service:3003
- `/api/v1/analytics/*` → analytics-service:3006 (Python FastAPI)

### Database Topology

Each NestJS service has its own Postgres instance (no shared DB):

| Service | DB name | Host port |
|---------|---------|-----------|
| auth-service | sentinel_auth | 5432 |
| camera-service | sentinel_camera | 5433 |
| incident-service | sentinel_incident | 5434 |
| user-service | sentinel_user | 5435 |
| alert-service | sentinel_alert | 5436 |
| analytics-service | omnisight_analytics (TimescaleDB) | 5441 |
| edge-database | sentinel_edge | 5438 |

Analytics uses **TimescaleDB** (time-series extension on Postgres 15) with `pgvector` for chatbot embeddings.

### Edge Node Registration Requirement

The incident-service validates every incoming `POST /api/v1/edge/sync` payload against the camera-service DB. The `edgeNodeCode` and `cameraCode` in the payload must already exist as registered records in camera-service. If they don't, the incident is rejected silently. When setting up a new environment, always create the zone → edge node → camera records first via the camera-service API.

### AI Detection Pipeline

The `ai-detection` service runs one `CameraPipeline` worker per camera. Each worker:
1. Reads frames from RTSP (native mode) or POSIX shared memory (docker IPC mode)
2. Accumulates `MICRO_BATCH_SECONDS` (default 10s) of frames into a temp video file
3. Runs enabled detectors in sequence: `crime_skelnet`, `weapon_detection`, `video_mae`, `surveillance_analytics`
4. Calls `StreamingFusionEngine.fuse()` to produce a per-frame score array
5. PAAN audio runs in a parallel thread (taps RTSP audio via ffmpeg every 5s); its score is applied as an **additive boost** on top of the fused video score, not as a weighted pool member — `final = clip(video_fused + paan_score × 0.65, 0, 1)`
6. If `fusion_score > ANOMALY_THRESHOLD` for `MIN_ANOMALY_DURATION` seconds, dispatches to incident-service

Fusion weights (configurable via env):
- `crime_skelnet`: 0.45
- `weapon_detection`: 0.25
- `video_mae`: 0.05
- `surveillance_analytics`: 0.00 (off by default)
- PAAN: additive boost strength 0.65 (not in weighted pool)

The Dockerfile for ai-detection is at `backend/apps/ai-detection/Dockerfile` but the build context must be the **repo root** because it copies from `ai/` which is outside `backend/`.

### MJPEG Stream

`GET http://localhost:8010/stream/:cameraCode` — served directly by ai-detection, no gateway, no auth. Returns an MJPEG multipart stream with the detection overlay rendered. Use `<img src="...">` in the browser — no player library needed.

### VLM + S3 Clip Flow

When an anomaly is confirmed:
1. ai-detection encodes the anomaly frames to MP4 and uploads to S3 (`clips/{cameraId}/{eventId}.mp4`)
2. Generates a presigned URL (7-day TTL) and patches it onto the incident as `videoUrl`
3. Posts a VLM analysis record to analytics-service (`POST /api/v1/analytics/vlm/ingest`)
4. The incident's `videoUrl` field contains the presigned S3 URL — pass it directly to a `<video>` element

### Kafka Topics

- `incidents` — incident-service publishes new/updated incidents; analytics-service consumes for time-series ingestion; alert-service consumes to trigger push notifications

### Angular Frontend Design System

The frontend uses a custom design system with **signal inputs**. Strict rules enforced by `.windsurf/rules/angular-ui-standards.md`:
- Use `<app-button>` — never raw `<button>`
- Use `<app-input [control]="...">` — never raw `<input>`
- Use `<app-main-card>` for all card/panel containers
- Component inputs are Angular signals — call them as functions in templates: `value()`, `isLoading()`
- Do not modify the core design system component source files

### Chatbot

The analytics-service chatbot uses **Groq** (llama-3.3-70b-versatile) with tool calls that query the Postgres/TimescaleDB directly. Sessions are stored in Redis with a TTL. Embeddings for semantic search use `fastembed` + `pgvector`. Set `GROQ_API_KEY` in the analytics-service env to enable it.

---

## Existing `ai/CLAUDE.md`

The `ai/` subdirectory has its own CLAUDE.md covering the standalone pipeline, component training scripts, and model weight locations. Read it before working on the AI components.
