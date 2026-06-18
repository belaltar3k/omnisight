import { UserRole } from "@shared/enums";

// GetCurrentUser function interface
export interface ICurrentUserResponse {
  sub: string;
  email: string;
  role: UserRole;
}