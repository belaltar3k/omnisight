import { inject, Injectable } from "@angular/core";
import { zoneApiEndpoints } from "@environments";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";
import {
  ICreateZoneRequest,
  ICreateZoneResponse,
  IUpdateZoneRequest,
  IZone,
} from "@shared/interfaces/zone";

@Injectable({
  providedIn: "root",
})
export class ZoneService {
  private readonly httpClient = inject(HttpClient);

  createZone(body: ICreateZoneRequest): Observable<ICreateZoneResponse> {
    return this.httpClient.post<ICreateZoneResponse>(
      zoneApiEndpoints.createZone,
      body,
    );
  }

  getZones(): Observable<IZone[]> {
    return this.httpClient.get<IZone[]>(zoneApiEndpoints.getZones);
  }

  getZoneById(id: string): Observable<IZone> {
    return this.httpClient.get<IZone>(zoneApiEndpoints.getZoneById(id));
  }

  updateZone(id: string, body: IUpdateZoneRequest): Observable<IZone> {
    return this.httpClient.patch<IZone>(zoneApiEndpoints.updateZone(id), body);
  }

  deleteZone(id: string): Observable<void> {
    return this.httpClient.delete<void>(zoneApiEndpoints.deleteZone(id));
  }
}
