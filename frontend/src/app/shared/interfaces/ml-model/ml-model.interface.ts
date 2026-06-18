export interface IMLModel {
  id: string;
  name: string;
  version: string;
  description?: string;
  modelType: string;
  accuracy?: number;
  status: "draft" | "deployed" | "archived";
  createdAt?: string;
  updatedAt?: string;
  type?: string;
  active?: boolean;
  f1?: number;
  latency?: number;
  updated?: string;
}
