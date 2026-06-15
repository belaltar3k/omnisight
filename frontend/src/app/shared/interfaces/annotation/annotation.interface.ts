export interface IAnnotation {
  id: string;
  title: string;
  description?: string;
  type: string;
  status: "pending" | "in-progress" | "completed";
  assignedTo?: string;
  dueDate?: string;
  cameraId?: string;
  createdAt?: string;
  updatedAt?: string;
  clips?: number;
}
