export interface IUpdateNotificationRequest {
  title?: string;
  message?: string;
  type?: "info" | "warning" | "error" | "success";
  read?: boolean;
}
