import { IMLModel } from "./ml-model.interface";

export interface ICreateMLModelRequest {
  name: string;
  version: string;
  description?: string;
  modelType: string;
  accuracy?: number;
}

export interface ICreateMLModelResponse extends IMLModel {}
