// UpdateZone function interface
import { IZone } from './zone.interface';

export interface IUpdateZoneRequest {
  name?: string;
  description?: string;
}

export interface IUpdateZoneResponse extends IZone {}