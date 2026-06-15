export interface IUpdateMLModelRequest {
  name?: string;
  version?: string;
  description?: string;
  modelType?: string;
  accuracy?: number;
  status?: "draft" | "deployed" | "archived";
}
