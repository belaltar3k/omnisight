import { CameraStatus } from "@shared/enums";

export interface ICamera {
  id: string;
  name: string;
  code: string;
  rtspUrl: string;
  status: CameraStatus;
  targetFps?: number;
  resolutionWidth?: number;
  resolutionHeight?: number;
  zoneId: string;
  edgeNodeId: string;
  createdAt?: string;
  location?: string;
  ip?: string;
  resolution?: string;
  fps?: number;
}
