# OmniSight Mobile API Reference

**Base URL:** `http://<SERVER_IP>:80`  
Everything goes through a single nginx proxy on **port 80**. No other ports need to be open.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Response Envelope](#2-response-envelope)
3. [Incidents](#3-incidents)
4. [Cameras & Live Stream](#4-cameras--live-stream)
5. [Zones & Edge Nodes](#5-zones--edge-nodes)
6. [Alerts](#6-alerts)
7. [Analytics](#7-analytics)
8. [Chatbot](#8-chatbot)
9. [User Profile](#9-user-profile)
10. [Device Tokens (Push Notifications)](#10-device-tokens-push-notifications)
11. [Common Types](#11-common-types)
12. [Error Responses](#12-error-responses)

---

## 1. Authentication

All endpoints except login/register require the header:

```
Authorization: Bearer <accessToken>
```

### Login

```
POST /api/v1/auth/login
```

**Body:**
```json
{
  "identifier": "admin@sentinel.com",
  "password": "Admin123!"
}
```
> `identifier` accepts either email **or** username.

**Response:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ..."
  }
}
```

---

### Refresh Access Token

```
POST /api/v1/auth/refresh
```

**Body:**
```json
{ "refreshToken": "eyJ..." }
```

**Response:** same shape as login — new `accessToken` + `refreshToken`.

---

### Register

```
POST /api/v1/auth/register
```

**Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecurePass1!",
  "role": "guard"
}
```

---

### Logout

```
POST /api/v1/auth/logout
Authorization: Bearer <token>
```

---

### Current User

```
GET /api/v1/auth/me
Authorization: Bearer <token>
```

---

## 2. Response Envelope

Every successful response is wrapped in:

```json
{
  "success": true,
  "data": { ... },
  "message": "Success"
}
```

Your application must read `response.data` — not the top level directly.

Paginated list responses have this shape inside `data`:

```json
{
  "data": [ ... ],
  "total": 142,
  "page": 1,
  "limit": 20,
  "totalPages": 8
}
```

---

## 3. Incidents

### List Incidents

```
GET /api/v1/incidents
Authorization: Bearer <token>
```

**Query params (all optional):**

| Param | Type | Example | Description |
|-------|------|---------|-------------|
| `page` | number | `1` | Page number (default 1) |
| `limit` | number | `20` | Items per page (default 20) |
| `status` | string | `new` | Filter: `new`, `detecting`, `acknowledged`, `investigating`, `dispatched`, `on_scene`, `resolved`, `false_positive` |
| `priority` | string | `critical` | Filter: `low`, `medium`, `high`, `critical` |
| `crimeType` | string | `theft` | Filter: `theft`, `assault`, `weapon`, `fire`, `vandalism`, `intrusion`, `shoplifting`, `accident`, `suspicious`, `abnormal` |
| `cameraId` | string | `uuid` | Filter by camera UUID |
| `startDate` | ISO 8601 | `2026-06-01T00:00:00Z` | |
| `endDate` | ISO 8601 | `2026-06-22T23:59:59Z` | |

**Response `data.data[]` item:**

```json
{
  "id": "uuid",
  "cameraId": "uuid",
  "cameraCode": "cam-001",
  "zoneId": "uuid",
  "crimeType": "theft",
  "confidence": 0.87,
  "status": "new",
  "priority": "high",
  "detectedAt": "2026-06-22T13:11:56Z",
  "videoUrl": "https://omnisight-bucket-storage.s3.amazonaws.com/clips/cam-001/abc.mp4?...",
  "thumbnailUrl": null,
  "vlmVerification": {
    "status": "completed",
    "verifiedCrimeType": "theft",
    "caption": "Man in blue hoodie appears to be stealing...",
    "anomalyScoreVlm": "HIGH",
    "peopleCount": 2,
    "observedEvents": ["person reaches into bag", "..."],
    "anomalyEvidence": ["item hidden behind back", "..."],
    "completedAt": "2026-06-22T13:11:56Z"
  },
  "aiMetadata": {
    "component_scores": {
      "crime_skelnet": 0.82,
      "weapon_detection": 0.21
    },
    "fused_peak": 0.71
  },
  "assignedTo": null,
  "resolvedAt": null,
  "createdAt": "2026-06-22T13:11:44Z"
}
```

---

### Get Incident

```
GET /api/v1/incidents/:id
Authorization: Bearer <token>
```

---

### Acknowledge

```
POST /api/v1/incidents/:id/acknowledge
Authorization: Bearer <token>
```

---

### Assign

```
POST /api/v1/incidents/:id/assign
Authorization: Bearer <token>
```

**Body:**
```json
{ "assignedTo": "user-uuid" }
```

---

### Resolve

```
POST /api/v1/incidents/:id/resolve
Authorization: Bearer <token>
```

**Body:**
```json
{ "resolutionNotes": "Officer attended, situation resolved." }
```

---

### Escalate

```
POST /api/v1/incidents/:id/escalate
Authorization: Bearer <token>
```

---

### Mark False Positive

```
POST /api/v1/incidents/:id/false-positive
Authorization: Bearer <token>
```

**Body:**
```json
{ "reason": "Camera misidentified movement as theft" }
```

---

### Timeline

```
GET /api/v1/incidents/:id/timeline
Authorization: Bearer <token>
```

**Response `data[]`:**
```json
[
  {
    "eventType": "created",
    "description": "Incident detected by AI pipeline",
    "timestamp": "2026-06-22T13:11:44Z"
  },
  {
    "eventType": "classified",
    "description": "Classified as theft with confidence 0.87",
    "timestamp": "2026-06-22T13:11:56Z"
  }
]
```

---

### Add Note

```
POST /api/v1/incidents/:id/notes
Authorization: Bearer <token>
```

**Body:**
```json
{
  "content": "Guard dispatched to location.",
  "noteType": "update"
}
```
> `noteType`: `general` | `update` | `resolution` | `handoff`

---

### Get Notes

```
GET /api/v1/incidents/:id/notes
Authorization: Bearer <token>
```

---

## 4. Cameras & Live Stream

### List Cameras

```
GET /api/v1/cameras
Authorization: Bearer <token>
```

**Response `data[]`:**
```json
[
  {
    "id": "uuid",
    "name": "Main Entrance",
    "code": "cam-001",
    "rtspUrl": "rtsp://...",
    "zoneId": "uuid",
    "edgeNodeId": "uuid",
    "status": "active"
  }
]
```

---

### Get Camera by Code

```
GET /api/v1/cameras/by-code/:code
Authorization: Bearer <token>
```

---

### MJPEG Live Stream (no auth required)

```
GET /stream/:cameraCode
```

**Example:** `http://<SERVER_IP>/stream/cam-001`

- Returns a multipart `multipart/x-mixed-replace` MJPEG stream
- Use `<img>` or a native image view — **no video player needed**
- On mobile: load into an `ImageView` / `UIImageView` by continuously reading the multipart response, or use a library that handles MJPEG (e.g., `MjpegInputStream` on Android, `MJPEGView` on iOS)
- The stream has detection overlays (bounding boxes, scores) rendered on each frame
- No `Authorization` header needed — this endpoint is intentionally public

---

## 5. Zones & Edge Nodes

### List Zones

```
GET /api/v1/zones
Authorization: Bearer <token>
```

### Get Zone

```
GET /api/v1/zones/:id
Authorization: Bearer <token>
```

### List Edge Nodes

```
GET /api/v1/edge-nodes
Authorization: Bearer <token>
```

### Cameras by Zone

```
GET /api/v1/cameras/by-zone/:zoneId
Authorization: Bearer <token>
```

---

## 6. Alerts

### List Alerts

```
GET /api/v1/alerts
Authorization: Bearer <token>
```

**Query params:** `page`, `limit`, `status` (`pending` | `sent` | `acknowledged`)

**Response `data[]`:**
```json
[
  {
    "id": "uuid",
    "incidentId": "uuid",
    "userId": "uuid",
    "alertType": "push",
    "message": "High priority incident: weapon detected at Main Entrance",
    "status": "sent",
    "sentAt": "2026-06-22T13:12:00Z"
  }
]
```

---

### Acknowledge Alert

```
POST /api/v1/alerts/:id/acknowledge
Authorization: Bearer <token>
```

---

### Alert Preferences

```
GET  /api/v1/alerts/preferences
PATCH /api/v1/alerts/preferences
Authorization: Bearer <token>
```

**Body for PATCH:**
```json
{
  "pushEnabled": true,
  "minPriority": "high",
  "crimeTypes": ["weapon", "assault", "fire"]
}
```

---

## 7. Analytics

### Dashboard Summary

```
GET /api/v1/analytics/dashboard/
Authorization: Bearer <token>
```

Returns incident counts by status, priority distribution, and recent activity.

---

### Incident Statistics

```
GET /api/v1/analytics/incidents/stats
Authorization: Bearer <token>
```

**Query:** `startDate`, `endDate`

---

### Incident Trends

```
GET /api/v1/analytics/incidents/trends
Authorization: Bearer <token>
```

**Query:** `startDate`, `endDate`, `interval` (`hour` | `day` | `week`)

---

### VLM Analyses

```
GET /api/v1/analytics/vlm/analyses
Authorization: Bearer <token>
```

Returns the AI vision model analysis records linked to incidents.

---

### VLM Summary

```
GET /api/v1/analytics/vlm/summary
Authorization: Bearer <token>
```

---

## 8. Chatbot

Powered by Groq (LLaMA 3.3 70B). Answers questions about incident data using live DB queries.

### Chat

```
POST /api/v1/analytics/chatbot/chat
Authorization: Bearer <token>
```

**Body:**
```json
{
  "message": "How many theft incidents happened yesterday?",
  "sessionId": "optional-uuid-to-continue-a-conversation"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "reply": "There were 12 theft incidents yesterday...",
    "sessionId": "uuid",
    "toolsUsed": ["query_incidents"]
  }
}
```

---

### Clear Session

```
DELETE /api/v1/analytics/chatbot/sessions/:sessionId
Authorization: Bearer <token>
```

---

## 9. User Profile

### Get Profile by Auth ID

```
GET /api/v1/profiles/auth/:authId
Authorization: Bearer <token>
```

### Update Profile

```
PATCH /api/v1/profiles/auth/:authId
Authorization: Bearer <token>
```

**Body:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "phoneNumber": "+1234567890"
}
```

---

## 10. Device Tokens (Push Notifications)

Register an FCM or APNs token to receive push alerts when incidents are created.

### Register Token

```
POST /api/v1/device-tokens
Authorization: Bearer <token>
```

**Body:**
```json
{
  "token": "FCM_OR_APNS_DEVICE_TOKEN",
  "platform": "android"
}
```
> `platform`: `android` | `ios`

---

### Unregister Token

```
DELETE /api/v1/device-tokens
Authorization: Bearer <token>
```

**Body:**
```json
{ "token": "FCM_OR_APNS_DEVICE_TOKEN" }
```

---

## 11. Common Types

### Incident Status

| Value | Meaning |
|-------|---------|
| `detecting` | AI pipeline is still processing |
| `new` | Classified, waiting for human review |
| `acknowledged` | Guard has seen it |
| `investigating` | Under active investigation |
| `dispatched` | Guard has been sent |
| `on_scene` | Guard is at location |
| `resolved` | Closed |
| `false_positive` | Marked as not a real incident |

### Priority

| Value | Colour (suggested) |
|-------|-------------------|
| `low` | blue |
| `medium` | yellow |
| `high` | orange |
| `critical` | red |

### Crime Types

`theft` · `assault` · `weapon` · `fire` · `vandalism` · `intrusion` · `shoplifting` · `accident` · `suspicious` · `abnormal`

### VLM Severity (`anomalyScoreVlm`)

`LOW` · `MEDIUM` · `HIGH`

---

## 12. Error Responses

All errors follow this envelope:

```json
{
  "success": false,
  "statusCode": 401,
  "message": "Unauthorized",
  "error": "You do not have permission"
}
```

| Code | Meaning |
|------|---------|
| 400 | Validation error — check `message` for details |
| 401 | Missing or invalid token — refresh or re-login |
| 403 | Token valid but role lacks permission |
| 404 | Resource not found |
| 500 | Server error |

---

## Quick-start: Authentication Flow

```
1. POST /api/v1/auth/login        → get accessToken + refreshToken
2. Store both tokens securely
3. Add "Authorization: Bearer <accessToken>" to every request
4. On 401 response → POST /api/v1/auth/refresh with refreshToken
5. On app start → register FCM token via POST /api/v1/device-tokens
```
