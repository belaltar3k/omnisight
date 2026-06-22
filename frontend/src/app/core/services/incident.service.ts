import { inject, Injectable } from '@angular/core';
import { incidentApiEndpoints } from '@environments';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { HttpClient, HttpParams } from '@angular/common/http';
import {
  IIncident,
  IIncidentNote,
  IIncidentEvidence,
  IIncidentTimelineEvent,
  ICreateIncidentRequest,
  IUpdateIncidentRequest,
  IAssignIncidentRequest,
  IResolveIncidentRequest,
  IMarkFalsePositiveRequest,
  IAddNoteRequest,
} from '@shared/interfaces/incident';
import { IncidentStatus, CrimeType, Priority } from '@shared/enums';

export interface IIncidentFilters {
  crimeType?: CrimeType[];
  status?: IncidentStatus[];
  priority?: Priority[];
  cameraId?: string;
  zoneId?: string;
  assignedTo?: string;
  dateFrom?: string;
  dateTo?: string;
  minConfidence?: number;
  hasAudio?: boolean;
  hasPose?: boolean;
  vlmVerified?: boolean;
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

@Injectable({
  providedIn: 'root',
})
export class IncidentService {
  private readonly httpClient = inject(HttpClient);

  createIncident(body: ICreateIncidentRequest): Observable<IIncident> {
    return this.httpClient.post<IIncident>(incidentApiEndpoints.createIncident, body);
  }

  getIncidents(filters?: IIncidentFilters): Observable<IIncident[]> {
    const params = this.buildFilterParams(filters);
    return this.httpClient.get<{ data: IIncident[]; total: number; page: number; limit: number; totalPages: number }>(
      incidentApiEndpoints.getIncidents, { params }
    ).pipe(map(r => r.data));
  }

  private buildFilterParams(filters?: IIncidentFilters): HttpParams {
    if (!filters) return new HttpParams();

    const entries: [string, string][] = [
      ...this.arrayParam('crime_type', filters.crimeType),
      ...this.arrayParam('status', filters.status),
      ...this.arrayParam('priority', filters.priority),
      ...this.stringParam('camera_id', filters.cameraId),
      ...this.stringParam('zone_id', filters.zoneId),
      ...this.stringParam('assigned_to', filters.assignedTo),
      ...this.stringParam('date_from', filters.dateFrom),
      ...this.stringParam('date_to', filters.dateTo),
      ...this.stringParam('sort_by', filters.sortBy),
      ...this.stringParam('sort_order', filters.sortOrder),
      ...(filters.minConfidence != null ? [['min_confidence', String(filters.minConfidence)] as [string, string]] : []),
      ...(filters.hasAudio != null ? [['has_audio', String(filters.hasAudio)] as [string, string]] : []),
      ...(filters.hasPose != null ? [['has_pose', String(filters.hasPose)] as [string, string]] : []),
      ...(filters.vlmVerified != null ? [['verified', String(filters.vlmVerified)] as [string, string]] : []),
      ...(filters.page ? [['page', String(filters.page)] as [string, string]] : []),
      ...(filters.limit ? [['limit', String(filters.limit)] as [string, string]] : []),
    ];

    return entries.reduce((p, [k, v]) => p.set(k, v), new HttpParams());
  }

  private arrayParam(key: string, values?: string[]): [string, string][] {
    return values?.length ? [[key, values.join(',')]] : [];
  }

  private stringParam(key: string, value?: string): [string, string][] {
    return value ? [[key, value]] : [];
  }

  getIncidentById(id: string): Observable<IIncident> {
    return this.httpClient.get<IIncident>(incidentApiEndpoints.getIncidentById(id));
  }

  updateIncident(id: string, body: IUpdateIncidentRequest): Observable<IIncident> {
    return this.httpClient.patch<IIncident>(incidentApiEndpoints.updateIncident(id), body);
  }

  deleteIncident(id: string): Observable<void> {
    return this.httpClient.delete<void>(incidentApiEndpoints.deleteIncident(id));
  }

  acknowledgeIncident(id: string): Observable<IIncident> {
    return this.httpClient.post<IIncident>(incidentApiEndpoints.acknowledgeIncident(id), {});
  }

  assignIncident(id: string, body: IAssignIncidentRequest): Observable<IIncident> {
    return this.httpClient.post<IIncident>(incidentApiEndpoints.assignIncident(id), body);
  }

  resolveIncident(id: string, body: IResolveIncidentRequest): Observable<IIncident> {
    return this.httpClient.post<IIncident>(incidentApiEndpoints.resolveIncident(id), body);
  }

  escalateIncident(id: string): Observable<IIncident> {
    return this.httpClient.post<IIncident>(incidentApiEndpoints.escalateIncident(id), {});
  }

  markFalsePositive(id: string, body: IMarkFalsePositiveRequest): Observable<IIncident> {
    return this.httpClient.post<IIncident>(incidentApiEndpoints.markFalsePositive(id), body);
  }

  getTimeline(id: string): Observable<IIncidentTimelineEvent[]> {
    return this.httpClient.get<IIncidentTimelineEvent[]>(incidentApiEndpoints.getTimeline(id));
  }

  addNote(id: string, body: IAddNoteRequest): Observable<IIncidentNote> {
    return this.httpClient.post<IIncidentNote>(incidentApiEndpoints.addNote(id), body);
  }

  getNotes(id: string): Observable<IIncidentNote[]> {
    return this.httpClient.get<IIncidentNote[]>(incidentApiEndpoints.getNotes(id));
  }

  getEvidence(id: string): Observable<IIncidentEvidence[]> {
    return this.httpClient.get<IIncidentEvidence[]>(incidentApiEndpoints.getEvidence(id));
  }

  uploadEvidence(id: string, file: File): Observable<IIncidentEvidence> {
    const formData = new FormData();
    formData.append('file', file);
    return this.httpClient.post<IIncidentEvidence>(incidentApiEndpoints.uploadEvidence(id), formData);
  }
}
