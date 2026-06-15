import { inject, Injectable } from '@angular/core';
import { annotationApiEndpoints } from '@environments';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import {
  IAnnotation,
  ICreateAnnotationRequest,
  IUpdateAnnotationRequest,
} from '@shared/interfaces/annotation';

@Injectable({
  providedIn: 'root',
})
export class AnnotationService {
  private readonly httpClient = inject(HttpClient);

  createTask(body: ICreateAnnotationRequest): Observable<IAnnotation> {
    return this.httpClient.post<IAnnotation>(annotationApiEndpoints.createTask, body);
  }

  getTasks(): Observable<IAnnotation[]> {
    return this.httpClient.get<IAnnotation[]>(annotationApiEndpoints.getTasks);
  }

  getTaskById(id: string): Observable<IAnnotation> {
    return this.httpClient.get<IAnnotation>(annotationApiEndpoints.getTaskById(id));
  }

  updateTask(id: string, body: IUpdateAnnotationRequest): Observable<IAnnotation> {
    return this.httpClient.patch<IAnnotation>(annotationApiEndpoints.getTaskById(id), body);
  }

  assignTask(id: string, body: { annotatorId: string }): Observable<IAnnotation> {
    return this.httpClient.post<IAnnotation>(annotationApiEndpoints.assignTask(id), body);
  }

  exportTask(id: string): Observable<Blob> {
    return this.httpClient.get(annotationApiEndpoints.exportTask(id), { responseType: 'blob' });
  }

  reviewTask(id: string, body: { approved: boolean; comments?: string }): Observable<IAnnotation> {
    return this.httpClient.post<IAnnotation>(annotationApiEndpoints.reviewTask(id), body);
  }

  getStats(): Observable<unknown> {
    return this.httpClient.get(annotationApiEndpoints.getStats);
  }
}
