import { inject, Injectable } from '@angular/core';
import { alertApiEndpoints } from '@environments';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import {
  IAlert,
  IAlertPreferences,
  IAcknowledgeAlertResponse,
  IUpdatePreferencesRequest,
} from '@shared/interfaces/alert';

@Injectable({
  providedIn: 'root',
})
export class AlertService {
  private readonly httpClient = inject(HttpClient);

  getAlerts(): Observable<IAlert[]> {
    return this.httpClient.get<IAlert[]>(alertApiEndpoints.getAlerts);
  }

  getAlertById(id: string): Observable<IAlert> {
    return this.httpClient.get<IAlert>(alertApiEndpoints.getAlertById(id));
  }

  acknowledgeAlert(id: string): Observable<IAcknowledgeAlertResponse> {
    return this.httpClient.post<IAcknowledgeAlertResponse>(
      alertApiEndpoints.acknowledgeAlert(id),
      {}
    );
  }

  getPreferences(): Observable<IAlertPreferences> {
    return this.httpClient.get<IAlertPreferences>(alertApiEndpoints.getPreferences);
  }

  updatePreferences(body: IUpdatePreferencesRequest): Observable<IAlertPreferences> {
    return this.httpClient.put<IAlertPreferences>(alertApiEndpoints.updatePreferences, body);
  }

  sendTestAlert(): Observable<void> {
    return this.httpClient.post<void>(alertApiEndpoints.sendTestAlert, {});
  }

  getHistory(): Observable<IAlert[]> {
    return this.httpClient.get<IAlert[]>(alertApiEndpoints.getHistory);
  }
}
