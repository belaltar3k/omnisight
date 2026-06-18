# Sentinel / OmniSight — Mobile API Reference

**Base URL:** `http://<server>:3000`

All responses (except analytics) are wrapped:
```json
{ "success": true, "statusCode": 200, "message": "...", "data": {} }
```

Error shape:
```json
{ "success": false, "statusCode": 400, "message": "...", "error": {} }
```

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [User Profiles](#2-user-profiles)
3. [Zone Assignments](#3-zone-assignments)
4. [Zones](#4-zones)
5. [Edge Nodes](#5-edge-nodes)
6. [Cameras](#6-cameras)
7. [Incidents](#7-incidents)
8. [Push Notifications](#8-push-notifications)
9. [Analytics](#9-analytics)
10. [Enumerations](#10-enumerations)
11. [Headers Reference](#11-headers-reference)

---

## 1. Authentication

All auth routes are **public** (no JWT required).

### POST `/api/v1/auth/register`

Create a new user account. Internally also creates a user profile.

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "min6chars",
  "fullName": "John Doe",
  "role": "security_guard",
  "phone": "optional",
  "avatarUrl": "optional",
  "jobTitle": "optional",
  "department": "optional",
  "shiftName": "optional",
  "emergencyContact": "optional",
  "emergencyPhone": "optional",
  "employeeCode": "optional",
  "address": "optional"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Account created successfully",
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "fullName": "John Doe",
    "role": "security_guard",
    "status": "active",
    "createdAt": "2024-01-01T00:00:00.000Z",
    "updatedAt": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### POST `/api/v1/auth/login`

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "fullName": "John Doe",
      "role": "security_guard"
    },
    "accessToken": "eyJ...",
    "refreshToken": "eyJ..."
  }
}
```

> `accessToken` expires in **15 minutes**. `refreshToken` expires in **7 days**.

---

### POST `/api/v1/auth/refresh`

**Request body:**
```json
{
  "refreshToken": "eyJ..."
}
```

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

### POST `/api/v1/auth/logout`

**Request body:**
```json
{
  "refreshToken": "eyJ..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

### POST `/api/v1/auth/forgot-password`

**Request body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Password reset email sent"
}
```

---

### POST `/api/v1/auth/reset-password`

**Request body:**
```json
{
  "email": "user@example.com",
  "token": "reset-token-from-email",
  "newPassword": "newpassword"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Password reset successful"
}
```

---

### GET `/api/v1/auth/me`

**Auth:** JWT Bearer required

Returns the decoded JWT payload for the current user.

**Response:**
```json
{
  "sub": "uuid",
  "email": "user@example.com",
  "role": "security_guard",
  "iat": 1700000000,
  "exp": 1700000900
}
```

---

## 2. User Profiles

**Auth:** JWT Bearer required for all routes.

### GET `/api/v1/profiles`

> **Roles:** `admin` only

Returns all user profiles.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "authUserId": "uuid",
      "fullName": "John Doe",
      "phone": "01012345678",
      "avatarUrl": "https://...",
      "jobTitle": "Guard",
      "department": "Security",
      "shiftName": "Night",
      "emergencyContact": "Jane Doe",
      "emergencyPhone": "01098765432",
      "employeeCode": "EMP001",
      "address": "Cairo, Egypt",
      "isActive": true,
      "createdAt": "2024-01-01T00:00:00.000Z",
      "updatedAt": "2024-01-01T00:00:00.000Z"
    }
  ]
}
```

---

### GET `/api/v1/profiles/auth/:authUserId`

> **Access:** Self or admin

**Path params:** `authUserId` (UUID)

**Response:**
```json
{
  "success": true,
  "data": { "...profile object..." }
}
```

---

### GET `/api/v1/profiles/auth/:authUserId/full`

> **Access:** Self or admin

**Path params:** `authUserId` (UUID)

Returns the profile plus all zone assignments.

**Response:**
```json
{
  "success": true,
  "data": {
    "profile": { "...profile object..." },
    "zoneAssignments": [ { "...assignment object..." } ]
  }
}
```

---

### PATCH `/api/v1/profiles/auth/:authUserId`

> **Access:** Self or admin

**Path params:** `authUserId` (UUID)

**Request body** (all fields optional):
```json
{
  "fullName": "string",
  "phone": "string",
  "avatarUrl": "string",
  "jobTitle": "string",
  "department": "string",
  "shiftName": "string",
  "emergencyContact": "string",
  "emergencyPhone": "string",
  "employeeCode": "string",
  "address": "string",
  "isActive": true
}
```

**Response:**
```json
{
  "success": true,
  "data": { "...updated profile object..." }
}
```

---

## 3. Zone Assignments

**Auth:** JWT Bearer required for all routes.

### POST `/api/v1/zone-assignments`

> **Roles:** `admin`, `supervisor`

**Request body:**
```json
{
  "authUserId": "uuid",
  "zoneId": "uuid",
  "notes": "optional"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "authUserId": "uuid",
    "zoneId": "uuid",
    "notes": "string",
    "assignedAt": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### GET `/api/v1/zone-assignments`

> **Roles:** `admin` only

Returns all zone assignments.

---

### GET `/api/v1/zone-assignments/zone/:zoneId`

> **Roles:** `admin`, `supervisor`

**Path params:** `zoneId` (UUID)

Returns all assignments for a specific zone.

---

### GET `/api/v1/zone-assignments/zone/:zoneId/users`

> **Roles:** `admin`, `supervisor`

**Path params:** `zoneId` (UUID)

Returns users with profiles assigned to a zone.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "assignment": { "...assignment object..." },
      "profile": { "...profile object..." }
    }
  ]
}
```

---

### GET `/api/v1/zone-assignments/user/:authUserId`

> **Roles:** `admin`, `supervisor`

**Path params:** `authUserId` (UUID)

Returns all zone assignments for a user.

---

### PATCH `/api/v1/zone-assignments/:id/reassign`

> **Roles:** `admin`, `supervisor`

**Path params:** `id` (assignment UUID)

**Request body:**
```json
{
  "newZoneId": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "data": { "...updated assignment object..." }
}
```

---

### DELETE `/api/v1/zone-assignments/:id`

> **Roles:** `admin`, `supervisor`

**Path params:** `id` (assignment UUID)

---

### DELETE `/api/v1/zone-assignments/user/:authUserId/zone/:zoneId`

> **Roles:** `admin`, `supervisor`

**Path params:** `authUserId` (UUID), `zoneId` (UUID)

---

## 4. Zones

**Auth:** JWT Bearer required for all routes.

### POST `/api/v1/zones`

> **Roles:** `admin`, `supervisor`

**Request body:**
```json
{
  "name": "Main Entrance",
  "description": "optional",
  "location": "optional"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Main Entrance",
    "description": "string",
    "location": "string",
    "createdAt": "2024-01-01T00:00:00.000Z",
    "updatedAt": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### GET `/api/v1/zones`

> **Roles:** Any authenticated user

Returns all zones.

---

### GET `/api/v1/zones/:id`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

---

### PATCH `/api/v1/zones/:id`

> **Roles:** `admin`, `supervisor`

**Path params:** `id` (UUID)

**Request body** (all optional):
```json
{
  "name": "string",
  "description": "string",
  "location": "string"
}
```

---

### DELETE `/api/v1/zones/:id`

> **Roles:** `admin` only

**Path params:** `id` (UUID)

---

## 5. Edge Nodes

**Auth:** JWT Bearer required for all routes.

### POST `/api/v1/edge-nodes`

> **Roles:** `admin` only

**Request body:**
```json
{
  "name": "Node A",
  "code": "EDGE-001",
  "ipAddress": "192.168.1.100",
  "status": "active",
  "maxCameras": 8
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Node A",
    "code": "EDGE-001",
    "ipAddress": "192.168.1.100",
    "status": "active",
    "maxCameras": 8,
    "createdAt": "2024-01-01T00:00:00.000Z",
    "updatedAt": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### GET `/api/v1/edge-nodes`

> **Roles:** `admin`, `supervisor`

---

### GET `/api/v1/edge-nodes/:id`

> **Roles:** `admin`, `supervisor`

**Path params:** `id` (UUID)

---

### GET `/api/v1/edge-nodes/by-code/:code`

> **Roles:** `admin`, `supervisor`

**Path params:** `code` (string)

---

### PATCH `/api/v1/edge-nodes/:id`

> **Roles:** `admin` only

**Path params:** `id` (UUID)

**Request body** (all optional):
```json
{
  "name": "string",
  "code": "string",
  "ipAddress": "string",
  "status": "active | inactive",
  "maxCameras": 8
}
```

---

### DELETE `/api/v1/edge-nodes/:id`

> **Roles:** `admin` only

**Path params:** `id` (UUID)

---

## 6. Cameras

**Auth:** JWT Bearer required for all routes.

### POST `/api/v1/cameras`

> **Roles:** `admin`, `supervisor`

**Request body:**
```json
{
  "name": "Camera 1",
  "code": "CAM-001",
  "rtspUrl": "rtsp://192.168.1.100/stream",
  "zoneId": "uuid",
  "edgeNodeId": "uuid",
  "status": "offline",
  "targetFps": 30,
  "resolutionWidth": 1920,
  "resolutionHeight": 1080
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Camera 1",
    "code": "CAM-001",
    "rtspUrl": "rtsp://...",
    "status": "offline",
    "targetFps": 30,
    "resolutionWidth": 1920,
    "resolutionHeight": 1080,
    "zoneId": "uuid",
    "edgeNodeId": "uuid",
    "createdAt": "2024-01-01T00:00:00.000Z",
    "updatedAt": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### GET `/api/v1/cameras`

> **Roles:** Any authenticated user

---

### GET `/api/v1/cameras/:id`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

---

### GET `/api/v1/cameras/by-code/:code`

> **Roles:** Any authenticated user

**Path params:** `code` (string)

---

### GET `/api/v1/cameras/by-zone/:zoneId`

> **Roles:** Any authenticated user

**Path params:** `zoneId` (UUID)

---

### GET `/api/v1/cameras/by-edge-node/:edgeNodeId`

> **Roles:** Any authenticated user

**Path params:** `edgeNodeId` (UUID)

---

### PATCH `/api/v1/cameras/:id`

> **Roles:** `admin`, `supervisor`

**Path params:** `id` (UUID)

**Request body** (all optional):
```json
{
  "name": "string",
  "code": "string",
  "rtspUrl": "string",
  "zoneId": "uuid",
  "edgeNodeId": "uuid",
  "status": "online | offline | error",
  "targetFps": 30,
  "resolutionWidth": 1920,
  "resolutionHeight": 1080
}
```

---

### DELETE `/api/v1/cameras/:id`

> **Roles:** `admin` only

**Path params:** `id` (UUID)

---

## 7. Incidents

**Auth:** JWT Bearer required for all routes.

### Incident Object

```json
{
  "id": "uuid",
  "cameraId": "uuid",
  "cameraCode": "CAM-001",
  "zoneId": "uuid",
  "edgeNodeId": "uuid",
  "trackId": "string",
  "crimeType": "assault",
  "confidence": 0.95,
  "status": "new",
  "priority": "high",
  "detectedAt": "2024-01-01T00:00:00.000Z",
  "modelVersion": "v1.0",
  "videoUrl": "https://...",
  "thumbnailUrl": "https://...",
  "aiMetadata": {},
  "assignedTo": "uuid",
  "assignedAt": "2024-01-01T00:00:00.000Z",
  "acknowledgedBy": "uuid",
  "acknowledgedAt": "2024-01-01T00:00:00.000Z",
  "resolvedBy": "uuid",
  "resolvedAt": "2024-01-01T00:00:00.000Z",
  "resolutionNotes": "string",
  "isFalsePositive": false,
  "falsePositiveReason": "string",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "updatedAt": "2024-01-01T00:00:00.000Z"
}
```

---

### State Machine

```
detecting → new → acknowledged → investigating → dispatched → on_scene → resolved
                ↘ false_positive (can exit from any state)
```

---

### GET `/api/v1/incidents`

> **Roles:** `admin`, `supervisor`

Returns paginated list of all incidents.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `crimeType` | string | Filter by crime type |
| `status` | string | Filter by status |
| `priority` | string | Filter by priority |
| `zoneId` | UUID | Filter by zone |
| `cameraId` | UUID | Filter by camera |
| `assignedTo` | UUID | Filter by assigned user |
| `dateFrom` | ISO8601 | Start of date range |
| `dateTo` | ISO8601 | End of date range |
| `minConfidence` | number (0–1) | Minimum AI confidence |
| `isFalsePositive` | boolean | Filter false positives |
| `page` | number | Default: `1` |
| `limit` | number | Default: `20` |
| `sortBy` | string | Default: `detectedAt` |
| `sortOrder` | `asc \| desc` | Default: `desc` |

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [ { "...incident object..." } ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```

---

### GET `/api/v1/incidents/my`

> **Roles:** Any authenticated user

Returns incidents assigned to the currently authenticated user. Accepts the same query params as the list above.

---

### GET `/api/v1/incidents/:id`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

---

### PATCH `/api/v1/incidents/:id`

> **Roles:** `admin`, `supervisor`

**Path params:** `id` (UUID)

**Request body** (all optional):
```json
{
  "crimeType": "assault",
  "priority": "high",
  "videoUrl": "string",
  "thumbnailUrl": "string",
  "modelVersion": "string"
}
```

---

### DELETE `/api/v1/incidents/:id`

> **Roles:** `admin` only

**Path params:** `id` (UUID)

---

### POST `/api/v1/incidents/:id/assign`

> **Roles:** `admin`, `supervisor`

**Path params:** `id` (UUID)

**Request body:**
```json
{
  "assignedTo": "uuid",
  "notes": "optional"
}
```

---

### POST `/api/v1/incidents/:id/acknowledge`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

**Request body:** `{}`

---

### POST `/api/v1/incidents/:id/investigate`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

**Request body:** `{}`

---

### POST `/api/v1/incidents/:id/dispatch`

> **Roles:** `admin`, `supervisor`

**Path params:** `id` (UUID)

**Request body:** `{}`

---

### POST `/api/v1/incidents/:id/on-scene`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

**Request body:** `{}`

---

### POST `/api/v1/incidents/:id/resolve`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

**Request body:**
```json
{
  "resolutionNotes": "optional string"
}
```

---

### POST `/api/v1/incidents/:id/false-positive`

> **Roles:** `admin`, `supervisor`

**Path params:** `id` (UUID)

**Request body:**
```json
{
  "reason": "required string"
}
```

---

### POST `/api/v1/incidents/:id/notes`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

**Request body:**
```json
{
  "content": "required string"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "incidentId": "uuid",
    "authorId": "uuid",
    "content": "string",
    "createdAt": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### GET `/api/v1/incidents/:id/notes`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

---

### GET `/api/v1/incidents/:id/timeline`

> **Roles:** Any authenticated user

**Path params:** `id` (UUID)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "incidentId": "uuid",
      "action": "string",
      "performedBy": "uuid",
      "fromStatus": "new",
      "toStatus": "acknowledged",
      "notes": "string",
      "createdAt": "2024-01-01T00:00:00.000Z"
    }
  ]
}
```

---

## 8. Push Notifications

**Auth:** JWT Bearer required for all routes.

Register the device FCM token after login and unregister it on logout. Notifications are sent automatically when a new incident is detected in a zone the user is assigned to.

### POST `/api/v1/device-tokens`

**Request body:**
```json
{
  "fcmToken": "firebase-cloud-messaging-token",
  "deviceType": "ios | android | web"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "authUserId": "uuid",
    "fcmToken": "string",
    "deviceType": "android",
    "createdAt": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### DELETE `/api/v1/device-tokens`

**Request body:**
```json
{
  "fcmToken": "firebase-cloud-messaging-token"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Token unregistered"
}
```

---

## 9. Analytics

**Auth:** JWT Bearer required.

All requests under `/api/v1/analytics/**` are proxied directly to the Python FastAPI analytics service. Responses are **not** wrapped in the standard NestJS envelope — they come back as-is from FastAPI.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/analytics/dashboard` | Dashboard summary metrics |
| GET | `/api/v1/analytics/incidents/heatmap` | Incident heatmap data |
| GET | `/api/v1/analytics/metrics` | KPIs and time-series stats |

Any `GET`, `POST`, `PATCH`, or `DELETE` under `/api/v1/analytics/` is forwarded verbatim with the JWT header.

---

## 10. Enumerations

### UserRole
```
admin | supervisor | security_guard
```

### UserStatus
```
active | inactive | locked
```

### CrimeType
```
abnormal | assault | theft | shoplifting | vandalism |
fire | weapon | intrusion | accident | suspicious
```

### IncidentStatus
```
detecting | new | acknowledged | investigating |
dispatched | on_scene | resolved | false_positive
```

### IncidentPriority
```
critical | high | medium | low
```

### CameraStatus
```
online | offline | error
```

### EdgeNodeStatus
```
active | inactive
```

---

## 11. Headers Reference

```
Authorization: Bearer <accessToken>     # All protected routes
```

### Token Lifecycle

1. Call `POST /api/v1/auth/login` → receive `accessToken` + `refreshToken`
2. Attach `accessToken` to every request as `Authorization: Bearer <token>`
3. When you receive a `401 Unauthorized`, call `POST /api/v1/auth/refresh` with the `refreshToken` to get a new pair
4. On logout, call `POST /api/v1/auth/logout` and `DELETE /api/v1/device-tokens` to clean up

### Role Permission Summary

| Resource | admin | supervisor | security_guard |
|----------|-------|------------|----------------|
| Profiles | full | self only | self only |
| Zones | full CRUD | create/read/update | read only |
| Edge Nodes | full CRUD | read only | — |
| Cameras | full CRUD | create/read/update | read only |
| Incidents (list all) | ✓ | ✓ | my only |
| Incidents (actions) | all | assign/dispatch/false-positive | ack/investigate/on-scene/resolve |
| Zone Assignments | full CRUD | full CRUD | — |
| Device Tokens | own | own | own |
