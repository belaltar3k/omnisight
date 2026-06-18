import { IDataset } from "./dataset.interface";

export interface ICreateDatasetRequest {
  name: string;
  description?: string;
}

export interface ICreateDatasetResponse extends IDataset {}
