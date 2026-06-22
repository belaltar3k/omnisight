export interface ILoginRequest {
  identifier: string;
  password: string;
}

export interface ILoginResponse {
  accessToken: string;
  refreshToken: string;
  user: {
    id: string;
    fullName: string;
    email: string;
    role: string;
  };
}