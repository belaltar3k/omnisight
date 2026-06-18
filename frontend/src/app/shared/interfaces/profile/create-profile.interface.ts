// CreateProfile function interface
import { IProfile } from './profile.interface';

export interface ICreateProfileRequest {
  authUserId: string;
  fullName: string;
  phone?: string;
  avatarUrl?: string;
  jobTitle?: string;
  department?: string;
  shiftName?: string;
  emergencyContact?: string;
  emergencyPhone?: string;
  employeeCode?: string;
  address?: string;
  isActive?: boolean;
}

export interface ICreateProfileResponse extends IProfile {}