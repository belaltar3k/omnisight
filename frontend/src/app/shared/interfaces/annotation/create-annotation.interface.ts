import { IAnnotation } from "./annotation.interface";

export interface ICreateAnnotationRequest {
  title: string;
  description?: string;
  type: string;
  assignedTo?: string;
  dueDate?: string;
  cameraId?: string;
}

export interface ICreateAnnotationResponse extends IAnnotation {}
