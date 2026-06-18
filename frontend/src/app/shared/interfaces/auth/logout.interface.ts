// Logout function interface
export interface ILogoutRequest {
  refreshToken: string;
}

export interface ILogoutResponse {
  message: string;
}