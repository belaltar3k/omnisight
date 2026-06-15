import { inject, Injectable } from "@angular/core";
import { authApiEndpoints } from "@environments";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import {
  ICurrentUserResponse,
  IForgotPasswordRequest,
  IForgotPasswordResponse,
  ILoginRequest,
  ILoginResponse,
  ILogoutRequest,
  ILogoutResponse,
  IRefreshTokenRequest,
  IRefreshTokenResponse,
  IRegisterRequest,
  IRegisterResponse,
  IResetPasswordRequest,
  IResetPasswordResponse,
} from "@shared/interfaces/auth";

@Injectable({
  providedIn: "root",
})
export class AuthService {
  private readonly httpClient = inject(HttpClient);

  register(body: IRegisterRequest): Observable<IRegisterResponse> {
    return this.httpClient.post<IRegisterResponse>(authApiEndpoints.register, body);
  }

  login(body: ILoginRequest): Observable<ILoginResponse> {
    return this.httpClient.post<ILoginResponse>(authApiEndpoints.login, body);
  }

  refreshToken(body: IRefreshTokenRequest): Observable<IRefreshTokenResponse> {
    return this.httpClient.post<IRefreshTokenResponse>(authApiEndpoints.refresh, body);
  }

  logout(body: ILogoutRequest): Observable<ILogoutResponse> {
    return this.httpClient.post<ILogoutResponse>(authApiEndpoints.logout, body);
  }

  getCurrentUser(): Observable<ICurrentUserResponse> {
    return this.httpClient.get<ICurrentUserResponse>(authApiEndpoints.me);
  }

  forgotPassword(body: IForgotPasswordRequest): Observable<IForgotPasswordResponse> {
    return this.httpClient.post<IForgotPasswordResponse>(authApiEndpoints.forgotPassword, body);
  }

  resetPassword(body: IResetPasswordRequest): Observable<IResetPasswordResponse> {
    return this.httpClient.post<IResetPasswordResponse>(authApiEndpoints.resetPassword, body);
  }
}
