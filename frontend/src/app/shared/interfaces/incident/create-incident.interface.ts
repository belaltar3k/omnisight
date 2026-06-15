import { CrimeType, Priority } from '@shared/enums';

export interface ICreateIncidentRequest {
  cameraId: string;
  zoneId: string;
  detectedBy: string;
  crimeType: CrimeType;
  confidence: number;
  detectedAt: string;
  priority?: Priority;
  modelVersion?: string;
  aiMetadata?: Record<string, unknown>;
}
