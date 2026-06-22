import { CrimeType, IncidentStatus, Priority } from '@shared/enums';

export interface IIncidentActor {
  trackId: string;
  role: 'suspect' | 'victim' | 'bystander' | 'subject';
  boundingBoxes: Record<string, [number, number, number, number]>;
  keypointsPerFrame: Record<string, Array<[number, number, number]>>;
  poseAction?: string;
  poseConfidence?: number;
  stGcnConfidence?: number;
}

export interface IVlmVerification {
  status: 'pending' | 'completed' | 'failed' | 'not_requested';
  verifiedCrimeType?: string;
  vlmConfidence?: number;
  isFalsePositive?: boolean;
  caption?: string;
  completedAt?: string;
  latencyMs?: number;
  anomalyScoreVlm?: string;
  observedEvents?: string[];
  anomalyEvidence?: string[];
  peopleCount?: number;
}

export interface IFusionScores {
  mil: number;
  flow: number;
  yolo: number;
  audio: number;
  rules: number;
  pose: number;
  total: number;
}

export interface IAudioTrigger {
  eventType: string;
  confidence: number;
  detectedAt: string;
}

export interface IIncidentNote {
  id: string;
  incidentId: string;
  authorId: string;
  authorName: string;
  content: string;
  noteType: 'general' | 'update' | 'resolution' | 'handoff' | 'vlm_review';
  createdAt: string;
}

export interface IIncidentEvidence {
  evidenceId: string;
  incidentId: string;
  evidenceType: 'video' | 'image' | 'audio' | 'document' | 'report';
  fileUrl: string;
  fileName: string;
  fileSizeBytes: number;
  uploadedBy: string;
  uploadedAt: string;
}

export interface IIncidentTimelineEvent {
  eventType: string;
  description: string;
  actor?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface IIncident {
  id: string;
  cameraId: string;
  cameraCode?: string;
  zoneId: string;
  edgeNodeId?: string;
  trackId?: string;
  crimeType: CrimeType;
  confidence: number;
  detectedAt: string;
  incidentStartTime?: string;
  incidentEndTime?: string;
  durationSeconds?: number;
  status: IncidentStatus;
  priority: Priority;
  modelVersion?: string;
  fusionScores?: IFusionScores;
  motionChaosScore?: number;
  audioTrigger?: IAudioTrigger;
  rulesViolated?: string[];
  poseAnomalyScore?: number;
  poseAction?: string;
  aiMetadata?: Record<string, unknown>;
  vlmVerification?: IVlmVerification;
  videoUrl?: string | null;
  thumbnailUrl?: string | null;
  assignedTo?: string | null;
  assignedAt?: string | null;
  acknowledgedBy?: string | null;
  acknowledgedAt?: string | null;
  resolvedAt?: string | null;
  resolvedBy?: string | null;
  resolutionNotes?: string | null;
  isFalsePositive?: boolean;
  falsePositiveReason?: string | null;
  deletedAt?: string | null;
  createdAt?: string;
  updatedAt?: string;
  actors?: IIncidentActor[];
}
