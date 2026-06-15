export interface IResetPasswordRequest {
  email: string;
  token: string;
  newPassword: string;
}

export interface IResetPasswordResponse {
  message: string;
}
