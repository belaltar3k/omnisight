import { ICamera } from './camera.interface';

export interface ICreateCameraRequest {
  name: string;
  code: string;
  rtspUrl: string;
  zoneId: string;
  edgeNodeId: string;
  targetFps?: number;
  resolutionWidth?: number;
  resolutionHeight?: number;
}

export interface ICreateCameraResponse extends ICamera {}