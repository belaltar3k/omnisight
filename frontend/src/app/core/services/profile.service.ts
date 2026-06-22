import { inject, Injectable } from "@angular/core";
import { profileApiEndpoints } from "@environments";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";
import {
  ICreateProfileRequest,
  ICreateProfileResponse,
  IFullProfileResponse,
  IProfile,
  IUpdateProfileRequest,
  IUpdateProfileResponse,
} from "@shared/interfaces/profile";

@Injectable({
  providedIn: "root",
})
export class ProfileService {
  private readonly httpClient = inject(HttpClient);

  createProfile(
    body: ICreateProfileRequest,
  ): Observable<ICreateProfileResponse> {
    return this.httpClient.post<ICreateProfileResponse>(
      profileApiEndpoints.createProfile,
      body,
    );
  }

  getProfiles(): Observable<IProfile[]> {
    return this.httpClient.get<IProfile[]>(profileApiEndpoints.getProfiles);
  }

  getProfileByAuthId(id: string): Observable<IProfile> {
    return this.httpClient.get<IProfile>(
      profileApiEndpoints.getProfileByAuthId(id),
    );
  }

  getFullProfile(id: string): Observable<IFullProfileResponse> {
    return this.httpClient.get<IFullProfileResponse>(
      profileApiEndpoints.getFullProfile(id),
    );
  }

  updateProfile(
    id: string,
    body: IUpdateProfileRequest,
  ): Observable<IUpdateProfileResponse> {
    return this.httpClient.patch<IUpdateProfileResponse>(
      profileApiEndpoints.updateProfile(id),
      body,
    );
  }

  deleteProfile(id: string): Observable<void> {
    return this.httpClient.delete<void>(profileApiEndpoints.deleteProfile(id));
  }
}
