import { EdgeNodeStatus } from "@shared/enums";

export interface IEdgeNode {
  id: string;
  name: string;
  code: string;
  ipAddress: string;
  status: EdgeNodeStatus | "online" | "degraded" | "offline";
  maxCameras: number;
  createdAt?: string;
  hostname?: string;
  location?: string;
  health?: number;
  gpu?: number;
  ram?: number;
  cameras?: number;
  heartbeat?: string;
}
