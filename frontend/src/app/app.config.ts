import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideToastr } from 'ngx-toastr';
import { routes } from './app.routes';
import { loadingInterceptor, errorInterceptor, successInterceptor, headerInterceptor, refreshInterceptor } from '@core/interceptors';


export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideToastr({
      timeOut: 4000,
      positionClass: 'toast-bottom-right',
      preventDuplicates: true,
      progressBar: true,
      progressAnimation: 'decreasing',
      closeButton: true,
      tapToDismiss: true,
      newestOnTop: true,
    }),
    provideHttpClient(withInterceptors([loadingInterceptor, headerInterceptor, refreshInterceptor, errorInterceptor, successInterceptor])),
  ],
};