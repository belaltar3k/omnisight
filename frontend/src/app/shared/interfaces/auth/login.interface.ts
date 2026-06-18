import { UserStatus } from "@shared/enums";

// Login function interface
export interface ILoginRequest {
  email: string;
  password: string;
}

export interface ILoginResponse {
  accessToken: string;
  refreshToken: string;

  user: {
    id: string;
    fullName: string;
    email: string;
    status: UserStatus;
  };
}