// CreateZone function interface
import { IZone } from './zone.interface';

export interface ICreateZoneRequest {
  name: string;
  description?: string;
}

export interface ICreateZoneResponse extends IZone {}