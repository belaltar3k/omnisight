export interface IUpdateTrainingJobRequest {
  name?: string;
  status?: "pending" | "running" | "completed" | "failed";
  progress?: number;
}
