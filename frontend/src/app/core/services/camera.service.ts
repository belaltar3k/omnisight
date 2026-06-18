import { inject, Injectable } from '@angular/core';
import { cameraApiEndpoints } from '@environments';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { ICamera, ICreateCameraRequest, ICreateCameraResponse, IUpdateCameraRequest } from '@shared/interfaces/camera';
@Injectable({
  providedIn: 'root',
})
export class CameraService {
   private readonly httpClient = inject(HttpClient);

  createCamera(
    body: ICreateCameraRequest
  ): Observable<ICreateCameraResponse> {
    return this.httpClient.post<ICreateCameraResponse>(
      cameraApiEndpoints.createCamera,
      body
    );
  }

  getCameras(): Observable<ICamera[]> {
    return this.httpClient.get<ICamera[]>(
      cameraApiEndpoints.getCameras
    );
  }

  getCameraById(id: string): Observable<ICamera> {
    return this.httpClient.get<ICamera>(
      cameraApiEndpoints.getCameraById(id)
    );
  }

  getCamerasByZone(zoneId: string): Observable<ICamera[]> {
    return this.httpClient.get<ICamera[]>(
      cameraApiEndpoints.getCamerasByZone(zoneId)
    );
  }

  getCamerasByEdgeNode(id: string): Observable<ICamera[]> {
    return this.httpClient.get<ICamera[]>(
      cameraApiEndpoints.getCamerasByEdgeNode(id)
    );
  }

  updateCamera(
    id: string,
    body: IUpdateCameraRequest
  ): Observable<ICamera> {
    return this.httpClient.patch<ICamera>(
      cameraApiEndpoints.updateCamera(id),
      body
    );
  }

  deleteCamera(id: string): Observable<void> {
    return this.httpClient.delete<void>(
      cameraApiEndpoints.deleteCamera(id)
    );
  }
}
