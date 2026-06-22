# OmniSight — Frontend Integration Guide

This document is the single source of truth for wiring the Angular frontend to the live backend.
Read it top to bottom before touching any service file. Every section calls out what exists in the
current code, what needs to change, and what needs to be built from scratch.

---

## 1. Architecture Overview

```
Browser (Angular 17 standalone)
  └── API Gateway  →  http://localhost:3000   (JWT-protected, all traffic goes here)
        ├── Auth Service          port 3001
        ├── User Service          port 3004   (profiles + zone assignments)
        ├── Camera Service        port 3012   (zones, edge nodes, cameras)
        ├── Incident Service      port 3003
        ├── Analytics Service     port 3006   (Python FastAPI — dashboard, stats, chatbot, VLM)
        └── AI Detection Service  port 8010   (internal only — do NOT call from browser)
```

All frontend calls go to **port 3000**. Do not hardcode any other port.

---

## 2. Environment File — Required Changes

**File:** `src/environments/environment.ts`

The current environment is missing the `analytics` base URL and the chatbot is pointed at the wrong
path. Replace the entire file with:

```typescript
const GATEWAY = `http://localhost:3000/api/v1`;

export const environment = {
  auth:           `${GATEWAY}/auth`,
  camera:         `${GATEWAY}/cameras`,
  profile:        `${GATEWAY}/profiles`,
  zoneAssignment: `${GATEWAY}/zone-assignments`,
  zone:           `${GATEWAY}/zones`,
  edgeNode:       `${GATEWAY}/edge-nodes`,
  incident:       `${GATEWAY}/incidents`,
  analytics:      `${GATEWAY}/analytics`,          // ADD THIS — was missing entirely
  deviceToken:    `${GATEWAY}/device-tokens`,      // push notification registration
  // ── REMOVE or leave as stubs (no backend routes exist for these) ──────────
  // alert, annotation, dataset, mlModel, training, notification, settings, user
  // These pages are in the routes but the services don't exist in the backend.
  // Keep the route shells but show a "Coming Soon" state until built.
};
```

---

## 3. Auth — Fixes Required

### 3.1 Login field name

**File:** `src/app/shared/interfaces/auth/login.interface.ts`

The API requires `identifier`, not `email`. Fix the interface:

```typescript
// BEFORE
export interface ILoginRequest {
  email: string;
  password: string;
}

// AFTER
export interface ILoginRequest {
  identifier: string;   // accepts email OR username
  password: string;
}
```

**File:** `src/app/features/auth/login/login.component.ts`

Change the form control name to match:
```typescript
// BEFORE
protected readonly loginForm = this.fb.nonNullable.group({
  email: ['', [Validators.required, Validators.email]],
  password: ['', [Validators.required]],
});

// AFTER
protected readonly loginForm = this.fb.nonNullable.group({
  identifier: ['', [Validators.required]],
  password: ['', [Validators.required]],
});
```

Update the HTML template label/placeholder accordingly (`email` → `identifier` or "Email / Username").

### 3.2 Login response shape

The API wraps everything in a `data` envelope:

```json
{
  "success": true,
  "data": {
    "accessToken": "...",
    "refreshToken": "...",
    "user": { "id": "...", "fullName": "...", "email": "...", "role": "ADMIN" }
  }
}
```

Fix `ILoginResponse`:
```typescript
export interface ILoginResponse {
  success: boolean;
  data: {
    accessToken: string;
    refreshToken: string;
    user: {
      id: string;
      fullName: string;
      email: string;
      role: string;
    };
  };
}
```

And update `login.component.ts` to use `response.data.accessToken` / `response.data.refreshToken`.

### 3.3 Refresh token response

Same envelope wrapping applies. `IRefreshTokenResponse.data.accessToken`.

---

## 4. Auth Endpoints

Base: `GET|POST http://localhost:3000/api/v1/auth/...`

| Method | Path | Body / Notes |
|--------|------|-------------|
| `POST` | `/auth/register` | `{ fullName, email, password, role? }` |
| `POST` | `/auth/login` | `{ identifier, password }` — **identifier not email** |
| `POST` | `/auth/refresh` | `{ refreshToken }` |
| `GET`  | `/auth/me` | Bearer token required — returns current user |
| `POST` | `/auth/logout` | `{ refreshToken }` |
| `POST` | `/auth/forgot-password` | `{ email }` |
| `POST` | `/auth/reset-password` | `{ token, newPassword }` |

---

## 5. User Profiles Endpoints

Base: `http://localhost:3000/api/v1/profiles`
All require Bearer token. Admin-only endpoints noted.

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/profiles` | Admin — create profile for an auth user |
| `GET`  | `/profiles` | Admin — list all profiles |
| `GET`  | `/profiles/auth/:authUserId` | Get profile by auth user ID |
| `GET`  | `/profiles/auth/:authUserId/full` | Profile + zone assignments |
| `PATCH`| `/profiles/auth/:authUserId` | Update profile |
| `DELETE`| `/profiles/auth/:authUserId` | **Missing from frontend** — add to `profileApiEndpoints` |

**Fix `profileApiEndpoints`** in `environment.ts`:
```typescript
export const profileApiEndpoints = {
  createProfile:      `${environment.profile}`,
  getProfiles:        `${environment.profile}`,
  getProfileByAuthId: (id: string) => `${environment.profile}/auth/${id}`,
  getFullProfile:     (id: string) => `${environment.profile}/auth/${id}/full`,
  updateProfile:      (id: string) => `${environment.profile}/auth/${id}`,
  deleteProfile:      (id: string) => `${environment.profile}/auth/${id}`,  // ADD
};
```

---

## 6. Zones Endpoints

Base: `http://localhost:3000/api/v1/zones`

| Method | Path | Body |
|--------|------|------|
| `POST` | `/zones` | `{ name, description?, location? }` |
| `GET`  | `/zones` | — |
| `GET`  | `/zones/:id` | — |
| `PATCH`| `/zones/:id` | partial update |
| `DELETE`| `/zones/:id` | — |

---

## 7. Edge Nodes Endpoints

Base: `http://localhost:3000/api/v1/edge-nodes`

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/edge-nodes` | `{ name, code, zoneId, ipAddress?, ... }` |
| `GET`  | `/edge-nodes` | list all |
| `GET`  | `/edge-nodes/:id` | by UUID |
| `GET`  | `/edge-nodes/by-code/:code` | **Missing from frontend** — look up by string code |
| `PATCH`| `/edge-nodes/:id` | partial update |
| `DELETE`| `/edge-nodes/:id` | — |

**Add to `edgeNodeApiEndpoints`:**
```typescript
getEdgeNodeByCode: (code: string) => `${environment.edgeNode}/by-code/${code}`,
```

---

## 8. Cameras Endpoints

Base: `http://localhost:3000/api/v1/cameras`

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/cameras` | `{ name, code, rtspUrl, zoneId, edgeNodeId, ... }` |
| `GET`  | `/cameras` | list all |
| `GET`  | `/cameras/:id` | by UUID |
| `GET`  | `/cameras/by-code/:code` | **Missing from frontend** — look up by string code |
| `GET`  | `/cameras/by-zone/:zoneId` | cameras in a zone |
| `GET`  | `/cameras/by-edge-node/:edgeNodeId` | cameras on an edge node |
| `PATCH`| `/cameras/:id` | partial update |
| `DELETE`| `/cameras/:id` | — |

**Add to `cameraApiEndpoints`:**
```typescript
getCameraByCode: (code: string) => `${environment.camera}/by-code/${code}`,
```

---

## 9. Incidents Endpoints

Base: `http://localhost:3000/api/v1/incidents`

| Method | Path | Notes |
|--------|------|-------|
| `GET`  | `/incidents` | supports `?page&limit&status&priority&cameraId&zoneId` |
| `GET`  | `/incidents/search` | `?q=...` full-text |
| `GET`  | `/incidents/:id` | |
| `POST` | `/incidents` | (usually created by AI, not manually) |
| `PATCH`| `/incidents/:id` | generic update |
| `DELETE`| `/incidents/:id` | |
| `POST` | `/incidents/:id/acknowledge` | `{ acknowledgedBy }` |
| `POST` | `/incidents/:id/assign` | `{ assignedTo }` |
| `POST` | `/incidents/:id/resolve` | `{ resolvedBy, resolution }` |
| `POST` | `/incidents/:id/escalate` | |
| `POST` | `/incidents/:id/false-positive` | |
| `GET`  | `/incidents/:id/timeline` | |
| `POST` | `/incidents/:id/notes` | `{ content, authorId }` |
| `GET`  | `/incidents/:id/notes` | |
| `GET`  | `/incidents/:id/evidence` | |
| `POST` | `/incidents/:id/evidence` | upload |

The `incidentApiEndpoints` in `environment.ts` already covers all of these — no changes needed.

---

## 10. Zone Assignments Endpoints

Base: `http://localhost:3000/api/v1/zone-assignments`

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/zone-assignments` | `{ authUserId, zoneId }` |
| `GET`  | `/zone-assignments` | list all |
| `GET`  | `/zone-assignments/user/:authUserId` | assignments for a user |
| `GET`  | `/zone-assignments/zone/:zoneId` | assignments for a zone |
| `GET`  | `/zone-assignments/zone/:zoneId/users` | users in a zone |
| `POST` | `/zone-assignments/:id/reassign` | change zone |
| `DELETE`| `/zone-assignments/user/:uid/zone/:zid` | remove by user+zone |
| `DELETE`| `/zone-assignments/:id` | remove by assignment ID |

`zoneAssignmentApiEndpoints` in `environment.ts` already covers these — no changes needed.

---

## 11. Device Tokens (Push Notifications)

Base: `http://localhost:3000/api/v1/device-tokens`

| Method | Path | Body |
|--------|------|------|
| `POST` | `/device-tokens/register` | `{ token, platform }` — FCM/APNS device token |
| `POST` | `/device-tokens/unregister` | `{ token }` |

Add to `environment.ts` and create a `DeviceTokenService` if push notifications are needed.

---

## 12. Analytics — Complete API Reference

**This is the most important section.** The analytics service is a Python FastAPI app.
The Angular environment has **no analytics key at all** — every endpoint below is currently uncalled.

Base: `http://localhost:3000/api/v1/analytics`
All require Bearer token (gateway enforces JWT).

### 12.1 Dashboard

```
GET /analytics/dashboard/
```
Returns a single object with all summary numbers for the main dashboard:

```json
{
  "total_incidents": 42,
  "incidents_today": 5,
  "active_cameras": 3,
  "total_cameras": 4,
  "resolved_rate": 0.78,
  "avg_response_time_minutes": 12.4,
  "critical_incidents": 2,
  "recent_incidents": [ { ...incident objects } ]
}
```

**The dashboard page should call this endpoint** instead of assembling metrics from four separate
service calls (cameras + zones + incidents + alerts). Replace the `combineLatest` in
`dashboard.component.ts` with a single `AnalyticsService.getDashboard()` call.

### 12.2 Incident Stats

```
GET /analytics/incidents/stats?date_from=ISO8601&date_to=ISO8601
```
Returns totals, by-status breakdown, by-priority breakdown, and top crime types.

### 12.3 Incident Trends

```
GET /analytics/incidents/trends?interval=D&date_from=ISO8601&date_to=ISO8601
```
`interval`: `H` (hour), `D` (day), `W` (week), `M` (month).
Returns a time-series array for charting.

### 12.4 Response Times

```
GET /analytics/incidents/response-times?date_from=ISO8601&date_to=ISO8601
```
Returns average/median/p95 response times per priority level.

### 12.5 Camera Performance

```
GET /analytics/cameras/performance?date_from=ISO8601&date_to=ISO8601
```
Per-camera incident counts, uptime, and anomaly rates.

### 12.6 Heatmap

```
GET /analytics/heatmap/?date_from=ISO8601&date_to=ISO8601
```
Returns zone-level density data for rendering an incident heatmap.

### 12.7 Surveillance Analytics (AI Detection Metrics)

These endpoints feed directly from the AI detection service's live data.

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/surveillance/summary` | Aggregated results from all 19 SA modules per camera |
| `GET /analytics/surveillance/latest` | Latest raw snapshot per camera (crowd count, traffic flow, motion level, etc.) |
| `GET /analytics/surveillance/crowd?hours=N` | Time-series crowd metrics, default `hours=1` |
| `GET /analytics/surveillance/traffic?hours=N` | Time-series traffic metrics |
| `POST /analytics/surveillance/ingest` | Internal — AI service posts snapshots here. Frontend reads only. |

**Surveillance summary response shape (per camera):**
```json
{
  "cameras": {
    "cam-001": {
      "crowd_count": 12,
      "motion_level": 0.73,
      "traffic_density": "HIGH",
      "loitering_detected": true,
      "fight_detected": false,
      "fusion_score": 0.61,
      "last_updated": "2026-06-22T14:32:00Z"
    }
  }
}
```

### 12.8 Reports

```
POST /analytics/reports/generate
```
Body:
```json
{
  "report_type": "incident_summary",   // or "camera_performance"
  "date_from": "2026-06-01T00:00:00Z",
  "date_to": "2026-06-22T23:59:59Z",
  "zone_ids": [],
  "camera_ids": [],
  "format": "json"
}
```

### 12.9 Chatbot

The chatbot is an AI assistant that can answer natural-language questions about incidents,
cameras, and surveillance data. It has memory per session.

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/analytics/chatbot/chat` | Send a message, get an answer |
| `GET`  | `/analytics/chatbot/sessions/:sessionId` | Retrieve full conversation history |
| `DELETE`| `/analytics/chatbot/sessions/:sessionId` | Clear session |

**Chat request:**
```json
{
  "message": "How many incidents happened in Zone A this week?",
  "session_id": "optional-uuid-to-continue-conversation"
}
```

**Chat response:**
```json
{
  "answer": "There were 7 incidents in Zone A between June 16–22...",
  "session_id": "uuid-for-this-session",
  "sources": [],
  "tools_used": ["query_incidents"]
}
```

If `session_id` is omitted, a new session is created. Store the returned `session_id` in the
component and pass it on every subsequent message for continuity.

**Fix `chatbotApiEndpoints`** in `environment.ts`:
```typescript
// BEFORE (wrong paths, wrong base)
export const chatbotApiEndpoints = {
  search:      `${environment.chatbot}/search`,
  sendMessage: `${environment.chatbot}/message`,
  getHistory:  `${environment.chatbot}/history`,
};

// AFTER
export const chatbotApiEndpoints = {
  chat:       `${environment.analytics}/chatbot/chat`,
  getSession: (id: string) => `${environment.analytics}/chatbot/sessions/${id}`,
  clearSession: (id: string) => `${environment.analytics}/chatbot/sessions/${id}`,
};
```

**Fix `ChatbotService`** (`src/app/core/services/chatbot.service.ts`):
```typescript
@Injectable({ providedIn: 'root' })
export class ChatbotService {
  private http = inject(HttpClient);

  chat(message: string, sessionId?: string): Observable<IChatResponse> {
    return this.http.post<IChatResponse>(chatbotApiEndpoints.chat, {
      message,
      session_id: sessionId ?? null,
    });
  }

  getSession(sessionId: string): Observable<{ session_id: string; messages: any[] }> {
    return this.http.get<any>(chatbotApiEndpoints.getSession(sessionId));
  }

  clearSession(sessionId: string): Observable<{ ok: boolean }> {
    return this.http.delete<any>(chatbotApiEndpoints.clearSession(sessionId));
  }
}
```

### 12.10 VLM Analysis

VLM (Visual Language Model) analyses are produced automatically by the AI pipeline when an
anomaly is detected. The frontend can read them for incident detail pages and the analytics view.

| Method | Path | Notes |
|--------|------|-------|
| `GET`  | `/analytics/vlm/analyses` | Query with `?camera_id=&zone=&crime_type=&hours=24&limit=50` |
| `GET`  | `/analytics/vlm/analyses/:analysisId` | Full detail including raw model caption |
| `GET`  | `/analytics/vlm/summary?hours=24` | Counts by crime type + recent captions |
| `POST` | `/analytics/vlm/ingest` | Internal — AI service writes here. Frontend reads only. |

**VLM analysis object:**
```json
{
  "id": "uuid",
  "timestamp": "2026-06-22T14:30:00Z",
  "track_id": "track-001",
  "camera_id": "cam-001",
  "zone": "Zone A",
  "crime_type": "fight",
  "vlm_score": "HIGH",
  "people_count": 3,
  "caption": "Three individuals engaged in physical altercation near the entrance.",
  "events": ["fighting", "running"],
  "evidence": [],
  "video_url": "https://..."
}
```

Add `vlmApiEndpoints` to `environment.ts`:
```typescript
export const vlmApiEndpoints = {
  getAnalyses:   `${environment.analytics}/vlm/analyses`,
  getAnalysis:   (id: string) => `${environment.analytics}/vlm/analyses/${id}`,
  getSummary:    `${environment.analytics}/vlm/summary`,
};
```

---

## 13. The Comprehensive Dashboard — What It Should Show

The dashboard is the most important page. It must pull from **multiple analytics endpoints**
simultaneously and present a live operational picture. Here is the full spec:

### 13.1 Top Metrics Row (from `GET /analytics/dashboard/`)

| Metric | API field |
|--------|-----------|
| Total Incidents Today | `incidents_today` |
| Active Cameras | `active_cameras / total_cameras` |
| Resolved Rate | `resolved_rate` as % |
| Avg Response Time | `avg_response_time_minutes` + "min" |
| Critical Incidents | `critical_incidents` |

### 13.2 Camera Live Status Grid (from `GET /analytics/surveillance/latest`)

For each camera: show name, current fusion score as a progress bar (0–1 → 0%–100%), crowd count,
motion level, and a green/yellow/red status dot based on `fusion_score`:
- `< 0.40` → Normal (green)
- `0.40–0.55` → Caution (yellow)
- `> 0.55` → Anomaly (red)

Auto-refresh every 10 seconds.

### 13.3 Recent Incidents Feed (from `GET /incidents?limit=10&sort=desc`)

Show the 10 most recent incidents with: camera name, timestamp, crime type, priority badge, and
status. Clicking opens the incident detail page.

### 13.4 Incident Trend Sparkline (from `GET /analytics/incidents/trends?interval=H&date_from=...`)

A small line chart showing incident count per hour for the last 24 hours.

### 13.5 Surveillance Module Summary (from `GET /analytics/surveillance/summary`)

A compact table or card grid: one row per camera, columns for crowd count, motion level,
traffic density, loitering flag, fight flag, and last-updated timestamp.

### 13.6 VLM Recent Captions (from `GET /analytics/vlm/summary?hours=24`)

A feed of the most recent AI-generated scene captions. Show timestamp, camera, and the caption
text. This gives operators a natural-language understanding of what happened.

---

## 14. Analytics Page — Tab Breakdown

The current `analytics.component` renders the same component for all child routes. Each tab
should be a distinct view consuming the appropriate endpoints:

| Tab Route | Endpoint(s) | Chart Type |
|-----------|-------------|-----------|
| `/analytics/dashboard` | `/analytics/dashboard/` | KPI cards |
| `/analytics/incidents` | `/analytics/incidents/stats` + `/trends` | Bar + line |
| `/analytics/heatmap` | `/analytics/heatmap/` | Zone heat map (e.g. ngx-heatmap or SVG) |
| `/analytics/response-times` | `/analytics/incidents/response-times` | Box plot or bar |
| `/analytics/surveillance` | `/analytics/surveillance/summary` + `/crowd` + `/traffic` | Table + time-series |
| `/analytics/vlm-performance` | `/analytics/vlm/analyses` + `/summary` | Table + caption feed |
| `/analytics/reports` | `POST /analytics/reports/generate` | Form → download JSON |
| `/analytics/audio-triggers` | `/analytics/surveillance/summary` (filter PAAN columns) | Table |

---

## 15. Services That Do NOT Exist in the Backend

The following routes exist in `app.routes.ts` and have services in `environment.ts`, but the
backend has **no matching API**. These pages should be left as UI shells with a "Coming Soon"
or empty-state placeholder rather than making broken HTTP calls:

| Frontend Route | Missing Backend |
|----------------|----------------|
| `/alerts` | No alerts CRUD service — incidents + device-token notifications replace this |
| `/annotations` | No annotation service |
| `/datasets` | No dataset service |
| `/ml-models` | No ML model management service |
| `/training` | No training job service |
| `/settings` | No settings service |
| `/notifications` | No notification read/write service (only device token registration) |
| `/users` (CRUD) | Use `/profiles` + auth-service `/auth/register` instead |

For the `/users` route specifically: creating a user means calling `POST /auth/register` to
create the auth record, then `POST /profiles` to create the profile. Listing users means
`GET /profiles`.

---

## 16. AnalyticsService — New Service to Create

Create `src/app/core/services/analytics.service.ts`:

```typescript
import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@environments';

const BASE = environment.analytics;

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private http = inject(HttpClient);

  getDashboard(): Observable<any> {
    return this.http.get(`${BASE}/dashboard/`);
  }

  getIncidentStats(dateFrom: string, dateTo: string): Observable<any> {
    return this.http.get(`${BASE}/incidents/stats`, {
      params: { date_from: dateFrom, date_to: dateTo }
    });
  }

  getIncidentTrends(dateFrom: string, dateTo: string, interval = 'D'): Observable<any> {
    return this.http.get(`${BASE}/incidents/trends`, {
      params: { date_from: dateFrom, date_to: dateTo, interval }
    });
  }

  getResponseTimes(dateFrom: string, dateTo: string): Observable<any> {
    return this.http.get(`${BASE}/incidents/response-times`, {
      params: { date_from: dateFrom, date_to: dateTo }
    });
  }

  getCameraPerformance(dateFrom: string, dateTo: string): Observable<any> {
    return this.http.get(`${BASE}/cameras/performance`, {
      params: { date_from: dateFrom, date_to: dateTo }
    });
  }

  getHeatmap(dateFrom: string, dateTo: string): Observable<any> {
    return this.http.get(`${BASE}/heatmap/`, {
      params: { date_from: dateFrom, date_to: dateTo }
    });
  }

  getSurveillanceSummary(): Observable<any> {
    return this.http.get(`${BASE}/surveillance/summary`);
  }

  getSurveillanceLatest(): Observable<any> {
    return this.http.get(`${BASE}/surveillance/latest`);
  }

  getCrowdMetrics(hours = 1): Observable<any> {
    return this.http.get(`${BASE}/surveillance/crowd`, { params: { hours } });
  }

  getTrafficMetrics(hours = 1): Observable<any> {
    return this.http.get(`${BASE}/surveillance/traffic`, { params: { hours } });
  }

  generateReport(body: any): Observable<any> {
    return this.http.post(`${BASE}/reports/generate`, body);
  }

  getVlmAnalyses(params?: any): Observable<any> {
    return this.http.get(`${BASE}/vlm/analyses`, { params });
  }

  getVlmAnalysis(id: string): Observable<any> {
    return this.http.get(`${BASE}/vlm/analyses/${id}`);
  }

  getVlmSummary(hours = 24): Observable<any> {
    return this.http.get(`${BASE}/vlm/summary`, { params: { hours } });
  }
}
```

Add `AnalyticsService` to `src/app/core/services/index.ts`.

---

## 17. Header Interceptor — Token Field

**File:** `src/app/core/interceptors/header-interceptor.ts`

Verify it reads the token from cookies with key `accessToken` (not `token`).
The login component stores it as `cookieService.set('accessToken', response.data.accessToken)`.

---

## 18. Admin Credentials (for testing)

```
identifier: admin@omnisight.ai
password:   Admin1234!
```

---

## 19. Quick Checklist Before Handoff Review

- [ ] `environment.ts` — `analytics` key added, `chatbot` pointing at analytics service
- [ ] `ILoginRequest` — `identifier` not `email`
- [ ] `ILoginResponse` — unwrapped from `data` envelope
- [ ] `profileApiEndpoints` — `deleteProfile` added
- [ ] `edgeNodeApiEndpoints` — `getEdgeNodeByCode` added
- [ ] `cameraApiEndpoints` — `getCameraByCode` added
- [ ] `chatbotApiEndpoints` — corrected to `/analytics/chatbot/chat` + sessions
- [ ] `ChatbotService` — refactored to use new endpoints + session_id pattern
- [ ] `AnalyticsService` — new service created and exported from `services/index.ts`
- [ ] Dashboard — uses `AnalyticsService.getDashboard()` instead of 4-way combineLatest
- [ ] Dashboard — surveillance live grid from `getSurveillanceLatest()` with 10s auto-refresh
- [ ] Analytics page — each tab calls its own endpoint, not the same component stub
- [ ] VLM analyses — service + endpoints wired for incident detail pages
- [ ] Dead routes (alerts, annotations, datasets, ml-models, training, settings) — show empty state
- [ ] `/users` management — uses `/profiles` + `/auth/register` instead of non-existent user CRUD

---

## 20. Live Camera Stream (Inference Overlay)

The AI detection service exposes an MJPEG stream per camera with the inference overlay burned in
(fusion score, bounding boxes, anomaly status):

```
GET http://localhost:8010/stream/:cameraCode
```

Example: `http://localhost:8010/stream/cam-001`

This endpoint is on the AI detection service directly — **not through the gateway** — and requires
no auth header. It is an internal, LAN-only stream.

### Where to embed it

Use a plain `<img>` tag. MJPEG over HTTP is natively supported by every browser as a streaming
image; no video player or HLS library needed.

```html
<!-- dashboard camera grid tile -->
<div class="camera-tile" *ngFor="let cam of cameras">
  <img
    [src]="'http://localhost:8010/stream/' + cam.code"
    [alt]="cam.name + ' live feed'"
    class="w-full h-full object-cover"
    (error)="onStreamError($event, cam)"
  />
  <span class="overlay-label">{{ cam.name }}</span>
</div>
```

```typescript
// In the component
onStreamError(event: Event, cam: Camera): void {
  (event.target as HTMLImageElement).src = '/assets/camera-offline.png';
}
```

### Where to show it in the UI

| Location | Behaviour |
|----------|-----------|
| Dashboard camera grid | Thumbnail-sized tile for every camera, auto-streams on load |
| Camera detail page (`/cameras/:id`) | Full-width panel at top, streams while page is open |
| Incident detail page (`/incidents/:id`) | If the incident is in `detecting` / `acknowledged` / `investigating` status and the camera is still live, show the stream alongside the incident record |

### Fusion score overlay data

The stream already has the score burned in visually. If you also want to show the raw number in
the UI, poll `GET /api/v1/analytics/surveillance/latest` every 10 seconds — it returns the
current `fusion_score` per camera alongside crowd count, motion level, and anomaly flag.

---

## 21. S3 Clip Playback — Review, Confirm, or Mark False Positive

When the AI pipeline detects an anomaly, it:
1. Encodes the anomaly frames into an MP4 clip
2. Uploads the clip to S3 bucket `omnisight-clips` under key `clips/{cameraId}/{eventId}.mp4`
3. Generates a **pre-signed URL** (valid for 7 days) and stores it in `incident.videoUrl`
4. Stores the same URL in `vlm_analysis.video_url`

The frontend can play the clip directly from the presigned URL — no proxy, no backend involvement.

### How to get the clip URL

From the incident object (returned by `GET /incidents/:id`):
```json
{
  "id": "uuid",
  "videoUrl": "https://omnisight-clips.s3.eu-north-1.amazonaws.com/clips/cam-001/event-abc.mp4?X-Amz-Signature=...",
  "thumbnailUrl": "https://...",
  "crimeType": "fight",
  "confidence": 0.87,
  "status": "new",
  "isFalsePositive": false,
  ...
}
```

`videoUrl` is the presigned S3 URL. Pass it directly to a `<video>` element.

### Clip Player Component

Create `src/app/features/incidents/incident-detail/clip-player.component.ts`:

```html
<!-- clip-player.component.html -->
<div class="clip-player" *ngIf="videoUrl; else noClip">
  <video
    #videoEl
    [src]="videoUrl"
    controls
    preload="metadata"
    class="w-full rounded-lg shadow-lg"
    (error)="onVideoError()"
  >
    Your browser does not support HTML5 video.
  </video>

  <!-- Action bar below the player -->
  <div class="action-bar mt-4 flex gap-3" *ngIf="!actioned">
    <button (click)="confirm()" class="btn btn-success">
      Confirm Incident
    </button>
    <button (click)="openFalsePositiveModal()" class="btn btn-outline-danger">
      Mark as False Positive
    </button>
  </div>

  <div *ngIf="actioned" class="status-pill mt-4">
    {{ actionMessage }}
  </div>
</div>

<ng-template #noClip>
  <div class="no-clip-placeholder">
    No clip available for this incident.
  </div>
</ng-template>
```

```typescript
// clip-player.component.ts
@Component({
  selector: 'app-clip-player',
  standalone: true,
  templateUrl: './clip-player.component.html',
})
export class ClipPlayerComponent {
  @Input() videoUrl?: string;
  @Input() incidentId!: string;

  private incidentService = inject(IncidentService);

  actioned = false;
  actionMessage = '';

  confirm(): void {
    // Resolve with a note indicating operator confirmed after review
    this.incidentService.resolveIncident(this.incidentId, {
      resolutionNotes: 'Confirmed by operator after clip review.'
    }).subscribe(() => {
      this.actioned = true;
      this.actionMessage = 'Incident confirmed and resolved.';
    });
  }

  openFalsePositiveModal(): void {
    // Show a small modal to collect the reason, then call markFalsePositive
    const reason = prompt('Reason for false positive:');  // replace with modal
    if (!reason) return;

    this.incidentService.markFalsePositive(this.incidentId, { reason })
      .subscribe(() => {
        this.actioned = true;
        this.actionMessage = 'Marked as false positive.';
      });
  }

  onVideoError(): void {
    console.warn('Clip URL may have expired (presigned URLs last 7 days).');
  }
}
```

### API calls used for clip review actions

**Confirm (resolve) an incident:**
```
POST /api/v1/incidents/:id/resolve
Body: { "resolutionNotes": "Confirmed by operator after clip review." }
```
Sets `status → resolved`.

**Mark as false positive:**
```
POST /api/v1/incidents/:id/false-positive
Body: { "reason": "Person was a staff member not an intruder." }
```
Sets `status → false_positive` and `isFalsePositive → true`.
Requires `ADMIN` or `SUPERVISOR` role — the JWT guard enforces this.

**Acknowledge first (if status is `new`):**
```
POST /api/v1/incidents/:id/acknowledge
```
No body required. Sets `status → acknowledged`. Call this automatically when the operator opens
the clip player if the incident is in `new` status.

### Incident status flow for clip review

```
detecting → new → acknowledged → (operator watches clip) → resolved
                                                         ↘ false_positive
```

Automate the `acknowledge` call when the clip player mounts so status updates without requiring
a manual button click.

### Where to show the clip player in the UI

**Incident Detail page** (`/incidents/:id`) — primary location:
- Top half: live stream tile (if incident is still active) OR clip player (if anomaly has ended)
- Right panel: incident metadata, timeline, notes
- Bottom: action bar (Confirm / False Positive / Assign / Escalate)

**Incidents list** (`/incidents`) — add a "Review" icon button on each row that opens a slide-over
panel with the clip player embedded, so operators can triage without leaving the list.

### Presigned URL expiry handling

The URL is valid for 7 days. If it has expired (video element fires `error`):
1. Show a message: "Clip expired — contact admin to re-generate."
2. The `thumbnailUrl` field (also stored on the incident) is a static S3 object and can be
   shown as a still frame fallback if the video URL has expired.

### IncidentService — ensure these methods exist

```typescript
// In incident.service.ts
resolveIncident(id: string, body: { resolutionNotes?: string }): Observable<any> {
  return this.http.post(incidentApiEndpoints.resolveIncident(id), body);
}

markFalsePositive(id: string, body: { reason: string }): Observable<any> {
  return this.http.post(incidentApiEndpoints.markFalsePositive(id), body);
}

acknowledgeIncident(id: string): Observable<any> {
  return this.http.post(incidentApiEndpoints.acknowledgeIncident(id), {});
}
```

These endpoint keys already exist in `incidentApiEndpoints` — just verify the service methods
are wired up and not returning stubs.

---

## 22. Updated Quick Checklist

Add these items to the checklist in section 19:

- [ ] Live MJPEG stream embedded in dashboard camera grid (`<img [src]="stream url">`)
- [ ] Camera detail page shows full-width stream panel
- [ ] Incident detail page shows stream when incident is active, clip player when ended
- [ ] `ClipPlayerComponent` created with `<video [src]="incident.videoUrl">` 
- [ ] Clip player auto-calls `acknowledge` on mount when status is `new`
- [ ] "Confirm Incident" button calls `POST /incidents/:id/resolve`
- [ ] "Mark as False Positive" button calls `POST /incidents/:id/false-positive` with reason
- [ ] `resolveIncident`, `markFalsePositive`, `acknowledgeIncident` methods exist in `IncidentService`
- [ ] Expired clip URL (`video error` event) shows fallback message + thumbnail
- [ ] Incidents list has "Review" quick-action that opens clip player slide-over
