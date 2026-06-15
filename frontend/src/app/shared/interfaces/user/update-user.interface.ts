import { UserRole, UserStatus } from '@shared/enums';

export interface IUpdateUserRequest {
  fullName?: string;
  email?: string;
  role?: UserRole;
  status?: UserStatus;
}
