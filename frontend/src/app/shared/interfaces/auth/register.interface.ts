import { UserRole } from "@shared/enums";

// Register function interface
export interface IRegisterRequest {
  email: string;
  password: string;
  fullName: string;
  role: UserRole;
  phone?: string;
  jobTitle?: string;
  department?: string;
  shiftName?: string;
  employeeCode?: string;
  address?: string;
  emergencyContact?: string;
  emergencyPhone?: string;
  avatarUrl?: string;
}

export interface IRegisterResponse {
  success: boolean;
  message: string;

  user: {
    id: string;
    email: string;
    role: UserRole;
  };
}
