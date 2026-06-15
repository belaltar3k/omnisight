import { inject, Injectable } from "@angular/core";
import { datasetApiEndpoints } from "@environments";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";
import {
  IDataset,
  ICreateDatasetRequest,
  IUpdateDatasetRequest,
} from "@shared/interfaces/dataset";

@Injectable({
  providedIn: "root",
})
export class DatasetService {
  private readonly httpClient = inject(HttpClient);

  createDataset(body: ICreateDatasetRequest): Observable<IDataset> {
    return this.httpClient.post<IDataset>(
      datasetApiEndpoints.createDataset,

      body,
    );
  }

  getDatasets(): Observable<IDataset[]> {
    return this.httpClient.get<IDataset[]>(datasetApiEndpoints.getDatasets);
  }

  getDatasetById(id: string): Observable<IDataset> {
    return this.httpClient.get<IDataset>(
      datasetApiEndpoints.getDatasetById(id),
    );
  }

  updateDataset(id: string, body: IUpdateDatasetRequest): Observable<IDataset> {
    return this.httpClient.patch<IDataset>(
      datasetApiEndpoints.updateDataset(id),
      body,
    );
  }

  deleteDataset(id: string): Observable<void> {
    return this.httpClient.delete<void>(datasetApiEndpoints.deleteDataset(id));
  }
}
