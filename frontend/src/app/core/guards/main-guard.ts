import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { CookieService } from 'ngx-cookie-service';

/** Prevents already-authenticated users from reaching login/forgot-password pages. */
export const mainGuard: CanActivateFn = () => {
  const cookieService = inject(CookieService);
  const router = inject(Router);

  if (cookieService.get('accessToken')) {
    return router.parseUrl('/dashboard');
  }

  return true;
};
