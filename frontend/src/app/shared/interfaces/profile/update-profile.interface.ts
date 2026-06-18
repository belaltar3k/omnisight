import { IProfile } from './profile.interface';

export interface IUpdateProfileRequest {
  phone?: string;
  jobTitle?: string;
  shiftName?: string;
  department?: string;
}

export interface IUpdateProfileResponse extends IProfile {}