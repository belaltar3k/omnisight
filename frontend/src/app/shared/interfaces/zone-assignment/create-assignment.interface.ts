import { IZoneAssignment } from "./zone-assignment.interface";

export interface ICreateZoneAssignmentRequest {
  authUserId: string;
  zoneId: string;
  notes?: string;
}

export interface ICreateZoneAssignmentResponse extends IZoneAssignment {}
