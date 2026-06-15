import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { CookieService } from 'ngx-cookie-service';
import { catchError, switchMap, throwError } from 'rxjs';
import { authApiEndpoints } from '@environments';
import { HttpClient } from '@angular/common/http';
import { IRefreshTokenResponse } from '@shared/interfaces/auth';
import { Router } from '@angular/router';

export const refreshInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const cookieService = inject(CookieService);
  const http = inject(HttpClient);
  const router = inject(Router);

  return next(req).pipe(
    catchError((err: unknown) => {
      if (
        !(err instanceof HttpErrorResponse) ||
        err.status !== 401 ||
        req.url.includes('/auth/refresh') ||
        req.url.includes('/auth/login')
      ) {
        return throwError(() => err);
      }

      const refreshToken = cookieService.get('refreshToken');
      if (!refreshToken) {
        cookieService.delete('accessToken');
        cookieService.delete('refreshToken');
        router.navigate(['/login']);
        return throwError(() => err);
      }

      return http.post<IRefreshTokenResponse>(authApiEndpoints.refresh, { refreshToken }).pipe(
        switchMap((tokens) => {
          cookieService.set('accessToken', tokens.accessToken, { path: '/' });
          cookieService.set('refreshToken', tokens.refreshToken, { path: '/' });

          const retried = req.clone({
            setHeaders: { Authorization: `Bearer ${tokens.accessToken}` },
          });
          return next(retried);
        }),
        catchError((refreshErr) => {
          cookieService.delete('accessToken');
          cookieService.delete('refreshToken');
          router.navigate(['/login']);
          return throwError(() => refreshErr);
        }),
      );
    }),
  );
};
