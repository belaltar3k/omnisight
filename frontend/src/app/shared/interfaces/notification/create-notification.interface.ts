import { INotification } from "./notification.interface";

export interface ICreateNotificationRequest {
  title: string;
  message: string;
  type: "info" | "warning" | "error" | "success";
  userId?: string;
  relatedId?: string;
}

export interface ICreateNotificationResponse extends INotification {}
