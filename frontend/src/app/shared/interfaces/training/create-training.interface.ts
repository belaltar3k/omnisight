import { ITrainingJob } from "./training.interface";

export interface ICreateTrainingJobRequest {
  name: string;
  modelId: string;
  datasetId: string;
}

export interface ICreateTrainingJobResponse extends ITrainingJob {}
