export interface INotification {
  id: string;
  title: string;
  message: string;
  type: "info" | "warning" | "error" | "success";
  read: boolean;
  userId?: string;
  relatedId?: string;
  createdAt?: string;
}
