import { UserRole, UserStatus } from '@shared/enums';

export interface IUser {
  id: string;
  fullName: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  createdAt?: string;
  updatedAt?: string;
}
