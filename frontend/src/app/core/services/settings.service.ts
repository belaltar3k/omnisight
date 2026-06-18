import { inject, Injectable } from "@angular/core";
import { settingsApiEndpoints } from "@environments";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";
import { ISettings, IUpdateSettingsRequest } from "@shared/interfaces/settings";

@Injectable({
  providedIn: "root",
})
export class SettingsService {
  private readonly httpClient = inject(HttpClient);

  getSettings(): Observable<ISettings> {
    return this.httpClient.get<ISettings>(settingsApiEndpoints.getSettings);
  }

  updateSettings(body: IUpdateSettingsRequest): Observable<ISettings> {
    return this.httpClient.put<ISettings>(
      settingsApiEndpoints.updateSettings,
      body,
    );
  }
}
