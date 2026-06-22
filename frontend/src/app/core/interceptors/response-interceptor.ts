import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { map } from 'rxjs';

export const responseInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    map((event) => {
      if (
        event instanceof HttpResponse &&
        event.body !== null &&
        typeof event.body === 'object' &&
        'success' in event.body &&
        'data' in event.body
      ) {
        return event.clone({ body: (event.body as any).data });
      }
      return event;
    }),
  );
};
