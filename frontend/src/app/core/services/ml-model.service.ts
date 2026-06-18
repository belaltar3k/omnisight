import { inject, Injectable } from '@angular/core';
import { mlModelApiEndpoints } from '@environments';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import {
  IMLModel,
  IUpdateMLModelRequest,
} from '@shared/interfaces/ml-model';

export interface IDeployModelRequest {
  targetNodes: string[];
  strategy: 'rolling' | 'blue-green' | 'canary';
  batchSize?: number;
  healthCheck?: boolean;
  rollbackOnFailure?: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class MLModelService {
  private readonly httpClient = inject(HttpClient);

  uploadModel(formData: FormData): Observable<IMLModel> {
    return this.httpClient.post<IMLModel>(mlModelApiEndpoints.uploadModel, formData);
  }

  getModels(): Observable<IMLModel[]> {
    return this.httpClient.get<IMLModel[]>(mlModelApiEndpoints.getModels);
  }

  getModelVersions(): Observable<IMLModel[]> {
    return this.httpClient.get<IMLModel[]>(mlModelApiEndpoints.getModelVersions);
  }

  getModelById(id: string): Observable<IMLModel> {
    return this.httpClient.get<IMLModel>(mlModelApiEndpoints.getModelById(id));
  }

  updateModel(id: string, body: IUpdateMLModelRequest): Observable<IMLModel> {
    return this.httpClient.patch<IMLModel>(mlModelApiEndpoints.getModelById(id), body);
  }

  deployModel(id: string, body: IDeployModelRequest): Observable<void> {
    return this.httpClient.post<void>(mlModelApiEndpoints.deployModel(id), body);
  }

  rollbackModel(id: string): Observable<void> {
    return this.httpClient.post<void>(mlModelApiEndpoints.rollbackModel(id), {});
  }

  getModelMetrics(id: string): Observable<unknown> {
    return this.httpClient.get(mlModelApiEndpoints.getModelMetrics(id));
  }

  getDeploymentHistory(id: string): Observable<unknown[]> {
    return this.httpClient.get<unknown[]>(mlModelApiEndpoints.getDeploymentHistory(id));
  }

  validateModel(id: string): Observable<void> {
    return this.httpClient.post<void>(mlModelApiEndpoints.validateModel(id), {});
  }

  promoteModel(id: string): Observable<IMLModel> {
    return this.httpClient.post<IMLModel>(mlModelApiEndpoints.promoteModel(id), {});
  }
}
