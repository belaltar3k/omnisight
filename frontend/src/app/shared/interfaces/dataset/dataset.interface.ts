export interface IDataset {
  id: string;
  name: string;
  description?: string;
  imageCount: number;
  annotationCount: number;
  status: "draft" | "ready" | "archived";
  createdBy?: string;
  createdAt?: string;
  updatedAt?: string;
  type?: string;
  videos?: number;
  features?: number;
  size?: string;
  created?: string;
}
