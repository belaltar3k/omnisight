export interface IRefreshTokenRequest {
  refreshToken: string;
}

export interface IRefreshTokenResponse {
  accessToken: string;
  refreshToken: string;
}