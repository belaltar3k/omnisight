import { inject, Injectable } from "@angular/core";
import { notificationApiEndpoints } from "@environments";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";
import {
  INotification,
  ICreateNotificationRequest,
  IUpdateNotificationRequest,
} from "@shared/interfaces/notification";

@Injectable({
  providedIn: "root",
})
export class NotificationService {
  private readonly httpClient = inject(HttpClient);

  createNotification(
    body: ICreateNotificationRequest,
  ): Observable<INotification> {
    return this.httpClient.post<INotification>(
      notificationApiEndpoints.createNotification,
      body,
    );
  }

  getNotifications(): Observable<INotification[]> {
    return this.httpClient.get<INotification[]>(
      notificationApiEndpoints.getNotifications,
    );
  }

  getNotificationById(id: string): Observable<INotification> {
    return this.httpClient.get<INotification>(
      notificationApiEndpoints.getNotificationById(id),
    );
  }

  updateNotification(
    id: string,
    body: IUpdateNotificationRequest,
  ): Observable<INotification> {
    return this.httpClient.patch<INotification>(
      notificationApiEndpoints.updateNotification(id),
      body,
    );
  }

  deleteNotification(id: string): Observable<void> {
    return this.httpClient.delete<void>(
      notificationApiEndpoints.deleteNotification(id),
    );
  }
}
