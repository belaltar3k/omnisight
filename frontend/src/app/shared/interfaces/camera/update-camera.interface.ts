import { CameraStatus } from "@shared/enums";
import { ICamera } from "./camera.interface";

export interface IUpdateCameraRequest {
  name?: string;
  rtspUrl?: string;
  status?: CameraStatus;
  zoneId?: string;
  edgeNodeId?: string;
}

export interface IUpdateCameraResponse extends ICamera {}
