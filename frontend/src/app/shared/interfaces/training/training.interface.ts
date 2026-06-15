import { JobStatus } from '@shared/enums';

export interface ITrainingJob {
  id: string;
  name: string;
  modelId: string;
  datasetId: string;
  status: JobStatus;
  progress?: number;
  startTime?: string;
  endTime?: string;
  createdAt?: string;
}