import { inject, Injectable } from '@angular/core';
import { trainingApiEndpoints } from '@environments';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import {
  ITrainingJob,
  ICreateTrainingJobRequest,
} from '@shared/interfaces/training';

@Injectable({
  providedIn: 'root',
})
export class TrainingService {
  private readonly httpClient = inject(HttpClient);

  submitJob(body: ICreateTrainingJobRequest): Observable<ITrainingJob> {
    return this.httpClient.post<ITrainingJob>(trainingApiEndpoints.submitJob, body);
  }

  getJobs(): Observable<ITrainingJob[]> {
    return this.httpClient.get<ITrainingJob[]>(trainingApiEndpoints.getJobs);
  }

  getJobById(id: string): Observable<ITrainingJob> {
    return this.httpClient.get<ITrainingJob>(trainingApiEndpoints.getJobById(id));
  }

  cancelJob(id: string): Observable<void> {
    return this.httpClient.delete<void>(trainingApiEndpoints.cancelJob(id));
  }

  resumeJob(id: string): Observable<ITrainingJob> {
    return this.httpClient.post<ITrainingJob>(trainingApiEndpoints.resumeJob(id), {});
  }

  getJobLogs(id: string): Observable<string[]> {
    return this.httpClient.get<string[]>(trainingApiEndpoints.getJobLogs(id));
  }

  getJobMetrics(id: string): Observable<unknown> {
    return this.httpClient.get(trainingApiEndpoints.getJobMetrics(id));
  }

  getDatasets(): Observable<unknown[]> {
    return this.httpClient.get<unknown[]>(trainingApiEndpoints.getDatasets);
  }

  uploadDataset(formData: FormData): Observable<unknown> {
    return this.httpClient.post(trainingApiEndpoints.uploadDataset, formData);
  }

  getExperiments(): Observable<unknown[]> {
    return this.httpClient.get<unknown[]>(trainingApiEndpoints.getExperiments);
  }
}
