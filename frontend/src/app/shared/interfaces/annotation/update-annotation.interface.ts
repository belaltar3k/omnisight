export interface IUpdateAnnotationRequest {
  title?: string;
  description?: string;
  type?: string;
  status?: "pending" | "in-progress" | "completed";
  assignedTo?: string;
  dueDate?: string;
  cameraId?: string;
}
