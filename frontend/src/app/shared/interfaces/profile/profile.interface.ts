export interface IProfile {
  id: string;
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
