import { inject, Injectable } from "@angular/core";
import { zoneAssignmentApiEndpoints } from "@environments";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";
import {
  ICreateZoneAssignmentRequest,
  ICreateZoneAssignmentResponse,
  IReassignZoneRequest,
  IReassignZoneResponse,
  IZoneAssignment,
} from "@shared/interfaces/zone-assignment";

@Injectable({
  providedIn: "root",
})
export class ZoneAssignmentService {
  private readonly httpClient = inject(HttpClient);

  createAssignment(
    body: ICreateZoneAssignmentRequest,
  ): Observable<ICreateZoneAssignmentResponse> {
    return this.httpClient.post<ICreateZoneAssignmentResponse>(
      zoneAssignmentApiEndpoints.createAssignment,
      body,
    );
  }

  getAssignments(): Observable<IZoneAssignment[]> {
    return this.httpClient.get<IZoneAssignment[]>(
      zoneAssignmentApiEndpoints.getAssignments,
    );
  }

  getAssignmentsByUser(id: string): Observable<IZoneAssignment[]> {
    return this.httpClient.get<IZoneAssignment[]>(
      zoneAssignmentApiEndpoints.getAssignmentsByUser(id),
    );
  }

  getAssignmentsByZone(id: string): Observable<IZoneAssignment[]> {
    return this.httpClient.get<IZoneAssignment[]>(
      zoneAssignmentApiEndpoints.getAssignmentsByZone(id),
    );
  }

  reassignZone(
    id: string,
    body: IReassignZoneRequest,
  ): Observable<IReassignZoneResponse> {
    return this.httpClient.patch<IReassignZoneResponse>(
      zoneAssignmentApiEndpoints.reassignZone(id),
      body,
    );
  }

  deleteById(id: string): Observable<void> {
    return this.httpClient.delete<void>(
      zoneAssignmentApiEndpoints.deleteById(id),
    );
  }
}
