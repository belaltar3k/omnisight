export interface IUpdateDatasetRequest {
  name?: string;
  description?: string;
  status?: "draft" | "ready" | "archived";
}
