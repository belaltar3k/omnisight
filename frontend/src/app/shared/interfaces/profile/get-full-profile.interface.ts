// GetFullProfile function interface
export interface IFullProfileResponse {
  authUserId: string;
  fullName: string;
  phone: string;
  jobTitle: string;
  department: string;
  shiftName: string;
  employeeCode: string;
  address: string;
  emergencyContact: string;
  emergencyPhone: string;
  avatarUrl: string;
  isActive: boolean;
}
