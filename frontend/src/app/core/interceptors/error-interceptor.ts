import { HttpInterceptorFn } from '@angular/common/http';
import {ToastrService} from "ngx-toastr";
import {catchError, throwError} from "rxjs";
import {inject} from "@angular/core";

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toastrService = inject(ToastrService);
  return next(req).pipe(
      catchError((err) => {
        toastrService.error(err?.error?.message ?? err?.message ?? 'An unexpected error occurred');
        return throwError(() => err);
      })
  );
};