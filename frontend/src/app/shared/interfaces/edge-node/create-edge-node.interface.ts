import { IEdgeNode } from './edge-node.interface';

export interface ICreateEdgeNodeRequest {
  name: string;
  code: string;
  ipAddress: string;
  maxCameras?: number;
}

export interface ICreateEdgeNodeResponse extends IEdgeNode {}